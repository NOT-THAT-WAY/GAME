using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace NotThatWay.Game.Topology
{
    public static class TopologyParser
    {
        public const int MaximumJsonBytes = 4 * 1024 * 1024;

        private static readonly Regex ChecksumPattern =
            new Regex("^[0-9a-f]{64}$", RegexOptions.CultureInvariant);

        public static TopologyParseResult Parse(string json)
        {
            return ParseInternal(json, false);
        }

        /// <summary>
        /// Point d'entree runtime. Contrairement a <see cref="Parse"/>, il refuse
        /// tout document non signe par son checksum canonique et toute topologie
        /// qui ne peut pas encore etre jouee.
        /// </summary>
        public static TopologyParseResult ParseVerified(string json)
        {
            return ParseInternal(json, true);
        }

        private static TopologyParseResult ParseInternal(string json, bool requireChecksum)
        {
            var issues = new List<TopologyIssue>();
            if (string.IsNullOrWhiteSpace(json))
            {
                Add(issues, TopologyIssueCodes.JsonInvalid, "$", "JSON vide.");
                return Invalid(issues);
            }
            if (Encoding.UTF8.GetByteCount(json) > MaximumJsonBytes)
            {
                Add(issues, TopologyIssueCodes.JsonTooLarge, "$", "Document JSON trop volumineux.");
                return Invalid(issues);
            }
            if (ContainsTrailingComma(json))
            {
                Add(issues, TopologyIssueCodes.JsonInvalid, "$", "Les virgules terminales sont interdites.");
                return Invalid(issues);
            }
            if (ContainsSingleQuoteOutsideString(json))
            {
                Add(issues, TopologyIssueCodes.JsonInvalid, "$", "Les chaines JSON doivent utiliser des guillemets doubles.");
                return Invalid(issues);
            }
            if (ContainsComment(json))
            {
                Add(issues, TopologyIssueCodes.JsonCommentForbidden, "$", "Les commentaires JSON sont interdits.");
                return Invalid(issues);
            }
            if (TryFindDuplicateProperty(json, out var duplicatePath))
            {
                Add(issues, TopologyIssueCodes.JsonPropertyDuplicate, duplicatePath, "Propriete JSON dupliquee.");
                return Invalid(issues);
            }

            JObject root;
            try
            {
                using var textReader = new StringReader(json);
                using var reader = new JsonTextReader(textReader)
                {
                    Culture = CultureInfo.InvariantCulture,
                    DateParseHandling = DateParseHandling.None,
                    FloatParseHandling = FloatParseHandling.Decimal,
                    MaxDepth = 64,
                    SupportMultipleContent = true
                };
                var token = JToken.Load(
                    reader,
                    new JsonLoadSettings
                    {
                        CommentHandling = CommentHandling.Load,
                        DuplicatePropertyNameHandling = DuplicatePropertyNameHandling.Error,
                        LineInfoHandling = LineInfoHandling.Load
                    });
                var containsComment = token.Type == JTokenType.Comment ||
                                      token is JContainer container &&
                                      container.Descendants().Any(item => item.Type == JTokenType.Comment);
                if (containsComment)
                    Add(issues, TopologyIssueCodes.JsonCommentForbidden, "$", "Les commentaires JSON sont interdits.");
                while (reader.Read())
                {
                    if (reader.TokenType == JsonToken.Comment)
                        Add(issues, TopologyIssueCodes.JsonCommentForbidden, "$", "Les commentaires JSON sont interdits.");
                    else if (reader.TokenType != JsonToken.None)
                        Add(issues, TopologyIssueCodes.JsonInvalid, "$", "Contenu apres le document JSON.");
                }
                root = token as JObject;
                if (root == null)
                    Add(issues, TopologyIssueCodes.JsonTypeInvalid, "$", "La racine doit etre un objet.");
            }
            catch (JsonReaderException error)
            {
                Add(
                    issues,
                    TopologyIssueCodes.JsonInvalid,
                    string.IsNullOrWhiteSpace(error.Path) ? "$" : "$.'" + error.Path + "'",
                    "JSON illisible.");
                return Invalid(issues);
            }

            if (issues.Count > 0 || root == null)
                return Invalid(issues);

            ValidateShape(root, issues);
            if (issues.Count > 0)
                return Invalid(issues);

            TopologyDocument document;
            try
            {
                var serializer = JsonSerializer.Create(
                    new JsonSerializerSettings
                    {
                        Culture = CultureInfo.InvariantCulture,
                        MissingMemberHandling = MissingMemberHandling.Error,
                        NullValueHandling = NullValueHandling.Include
                    });
                document = root.ToObject<TopologyDocument>(serializer);
            }
            catch (JsonSerializationException)
            {
                Add(issues, TopologyIssueCodes.JsonTypeInvalid, "$", "Un membre JSON n'a pas le type attendu.");
                return Invalid(issues);
            }

            issues.AddRange(requireChecksum
                ? TopologyValidator.ValidateForRuntime(document)
                : TopologyValidator.Validate(document));
            if (issues.Count == 0 && requireChecksum && string.IsNullOrEmpty(document.Checksum))
                Add(issues, TopologyIssueCodes.ChecksumRequired, "$.checksum", "Checksum runtime obligatoire.");

            if (issues.Count == 0 && !string.IsNullOrEmpty(document.Checksum))
            {
                if (!ChecksumPattern.IsMatch(document.Checksum))
                {
                    Add(issues, TopologyIssueCodes.ChecksumInvalid, "$.checksum", "Checksum SHA-256 invalide.");
                }
                else if (!string.Equals(
                             document.Checksum,
                             TopologyCanonicalizer.ComputeChecksum(document),
                             StringComparison.Ordinal))
                {
                    Add(issues, TopologyIssueCodes.ChecksumMismatch, "$.checksum", "Checksum different du contenu canonique.");
                }
            }

            return issues.Count == 0
                ? new TopologyParseResult(document, issues)
                : Invalid(issues);
        }

        private static void ValidateShape(JObject root, ICollection<TopologyIssue> issues)
        {
            ValidateMembers(
                root,
                "$",
                new[] { "schemaVersion", "topologyId", "dimensions", "openings", "walls", "pivots", "spawns" },
                new[] { "checksum" },
                issues);
            RequireType(root["schemaVersion"], JTokenType.Integer, "$.schemaVersion", issues);
            RequireType(root["topologyId"], JTokenType.String, "$.topologyId", issues);
            RequireOptionalType(root["checksum"], JTokenType.String, "$.checksum", issues);

            var dimensions = AsObject(root["dimensions"], "$.dimensions", issues);
            if (dimensions != null)
            {
                ValidateMembers(
                    dimensions,
                    "$.dimensions",
                    new[] { "widthCells", "heightCells", "cellPitchMm", "wallThicknessMm", "wallHeightMm" },
                    Array.Empty<string>(),
                    issues);
                foreach (var name in new[] { "widthCells", "heightCells", "cellPitchMm", "wallThicknessMm", "wallHeightMm" })
                    RequireType(dimensions[name], JTokenType.Integer, "$.dimensions." + name, issues);
            }

            ValidateOpenings(root["openings"], issues);
            ValidateWalls(root["walls"], issues);
            ValidatePivots(root["pivots"], issues);
            ValidateSpawns(root["spawns"], issues);
        }

        private static void ValidateOpenings(JToken token, ICollection<TopologyIssue> issues)
        {
            var array = AsArray(token, "$.openings", issues);
            if (array == null)
                return;
            for (var index = 0; index < array.Count; index++)
            {
                var path = $"$.openings[{index}]";
                var item = AsObject(array[index], path, issues);
                if (item == null)
                    continue;
                ValidateMembers(item, path, new[] { "openingId", "edge" }, Array.Empty<string>(), issues);
                RequireType(item["openingId"], JTokenType.Integer, path + ".openingId", issues);
                ValidateEdge(item["edge"], path + ".edge", issues);
            }
        }

        private static void ValidateWalls(JToken token, ICollection<TopologyIssue> issues)
        {
            var array = AsArray(token, "$.walls", issues);
            if (array == null)
                return;
            for (var index = 0; index < array.Count; index++)
            {
                var path = $"$.walls[{index}]";
                var item = AsObject(array[index], path, issues);
                if (item == null)
                    continue;
                ValidateMembers(
                    item,
                    path,
                    new[] { "wallId", "initialStateId", "states" },
                    new[] { "pivotId" },
                    issues);
                RequireType(item["wallId"], JTokenType.Integer, path + ".wallId", issues);
                RequireOptionalType(item["pivotId"], JTokenType.Integer, path + ".pivotId", issues, true);
                RequireType(item["initialStateId"], JTokenType.Integer, path + ".initialStateId", issues);
                var states = AsArray(item["states"], path + ".states", issues);
                if (states == null)
                    continue;
                for (var stateIndex = 0; stateIndex < states.Count; stateIndex++)
                {
                    var statePath = path + $".states[{stateIndex}]";
                    var state = AsObject(states[stateIndex], statePath, issues);
                    if (state == null)
                        continue;
                    ValidateMembers(
                        state,
                        statePath,
                        new[] { "stateId", "edge", "quarterTurns" },
                        Array.Empty<string>(),
                        issues);
                    RequireType(state["stateId"], JTokenType.Integer, statePath + ".stateId", issues);
                    ValidateEdge(state["edge"], statePath + ".edge", issues);
                    RequireType(state["quarterTurns"], JTokenType.Integer, statePath + ".quarterTurns", issues);
                }
            }
        }

        private static void ValidatePivots(JToken token, ICollection<TopologyIssue> issues)
        {
            var array = AsArray(token, "$.pivots", issues);
            if (array == null)
                return;
            for (var index = 0; index < array.Count; index++)
            {
                var path = $"$.pivots[{index}]";
                var item = AsObject(array[index], path, issues);
                if (item == null)
                    continue;
                ValidateMembers(item, path, new[] { "pivotId", "node", "wallIds" }, Array.Empty<string>(), issues);
                RequireType(item["pivotId"], JTokenType.Integer, path + ".pivotId", issues);
                ValidatePoint(item["node"], path + ".node", issues);
                var wallIds = AsArray(item["wallIds"], path + ".wallIds", issues);
                if (wallIds == null)
                    continue;
                for (var wallIndex = 0; wallIndex < wallIds.Count; wallIndex++)
                    RequireType(wallIds[wallIndex], JTokenType.Integer, path + $".wallIds[{wallIndex}]", issues);
            }
        }

        private static void ValidateSpawns(JToken token, ICollection<TopologyIssue> issues)
        {
            var array = AsArray(token, "$.spawns", issues);
            if (array == null)
                return;
            for (var index = 0; index < array.Count; index++)
            {
                var path = $"$.spawns[{index}]";
                var item = AsObject(array[index], path, issues);
                if (item == null)
                    continue;
                ValidateMembers(item, path, new[] { "spawnId", "cell", "yawQuarterTurns" }, Array.Empty<string>(), issues);
                RequireType(item["spawnId"], JTokenType.Integer, path + ".spawnId", issues);
                ValidatePoint(item["cell"], path + ".cell", issues);
                RequireType(item["yawQuarterTurns"], JTokenType.Integer, path + ".yawQuarterTurns", issues);
            }
        }

        private static void ValidateEdge(JToken token, string path, ICollection<TopologyIssue> issues)
        {
            var edge = AsObject(token, path, issues);
            if (edge == null)
                return;
            ValidateMembers(edge, path, new[] { "axis", "x", "y" }, Array.Empty<string>(), issues);
            RequireType(edge["axis"], JTokenType.String, path + ".axis", issues);
            RequireType(edge["x"], JTokenType.Integer, path + ".x", issues);
            RequireType(edge["y"], JTokenType.Integer, path + ".y", issues);
        }

        private static void ValidatePoint(JToken token, string path, ICollection<TopologyIssue> issues)
        {
            var point = AsObject(token, path, issues);
            if (point == null)
                return;
            ValidateMembers(point, path, new[] { "x", "y" }, Array.Empty<string>(), issues);
            RequireType(point["x"], JTokenType.Integer, path + ".x", issues);
            RequireType(point["y"], JTokenType.Integer, path + ".y", issues);
        }

        private static void ValidateMembers(
            JObject value,
            string path,
            IEnumerable<string> required,
            IEnumerable<string> optional,
            ICollection<TopologyIssue> issues)
        {
            var requiredSet = new HashSet<string>(required, StringComparer.Ordinal);
            var allowed = new HashSet<string>(requiredSet, StringComparer.Ordinal);
            allowed.UnionWith(optional);
            foreach (var property in value.Properties())
            {
                if (!allowed.Contains(property.Name))
                    Add(issues, TopologyIssueCodes.JsonMemberUnknown, path + "." + property.Name, "Membre JSON inconnu.");
            }
            foreach (var name in requiredSet)
            {
                if (value.Property(name, StringComparison.Ordinal) == null)
                    Add(issues, TopologyIssueCodes.JsonMemberMissing, path + "." + name, "Membre JSON requis absent.");
            }
        }

        private static JObject AsObject(JToken token, string path, ICollection<TopologyIssue> issues)
        {
            if (token == null)
                return null;
            if (token is JObject value)
                return value;
            Add(issues, TopologyIssueCodes.JsonTypeInvalid, path, "Objet JSON attendu.");
            return null;
        }

        private static JArray AsArray(JToken token, string path, ICollection<TopologyIssue> issues)
        {
            if (token == null)
                return null;
            if (token is JArray value)
                return value;
            Add(issues, TopologyIssueCodes.JsonTypeInvalid, path, "Tableau JSON attendu.");
            return null;
        }

        private static void RequireType(
            JToken token,
            JTokenType expected,
            string path,
            ICollection<TopologyIssue> issues)
        {
            if (token != null && token.Type != expected)
                Add(issues, TopologyIssueCodes.JsonTypeInvalid, path, $"Type {expected} attendu.");
        }

        private static void RequireOptionalType(
            JToken token,
            JTokenType expected,
            string path,
            ICollection<TopologyIssue> issues,
            bool allowNull = false)
        {
            if (token == null || allowNull && token.Type == JTokenType.Null)
                return;
            RequireType(token, expected, path, issues);
        }

        private static bool ContainsTrailingComma(string json)
        {
            var inString = false;
            var escaped = false;
            for (var index = 0; index < json.Length; index++)
            {
                var character = json[index];
                if (inString)
                {
                    if (escaped)
                        escaped = false;
                    else if (character == '\\')
                        escaped = true;
                    else if (character == '"')
                        inString = false;
                    continue;
                }
                if (character == '"')
                {
                    inString = true;
                    continue;
                }
                if (character != ',')
                    continue;

                var next = index + 1;
                while (next < json.Length && char.IsWhiteSpace(json[next]))
                    next++;
                if (next < json.Length && (json[next] == ']' || json[next] == '}'))
                    return true;
            }
            return false;
        }

        private static bool ContainsComment(string json)
        {
            var inString = false;
            var escaped = false;
            for (var index = 0; index + 1 < json.Length; index++)
            {
                var character = json[index];
                if (inString)
                {
                    if (escaped)
                        escaped = false;
                    else if (character == '\\')
                        escaped = true;
                    else if (character == '"')
                        inString = false;
                    continue;
                }
                if (character == '"')
                {
                    inString = true;
                    continue;
                }
                if (character == '/' && (json[index + 1] == '/' || json[index + 1] == '*'))
                    return true;
            }
            return false;
        }

        private static bool ContainsSingleQuoteOutsideString(string json)
        {
            var inString = false;
            var escaped = false;
            foreach (var character in json)
            {
                if (inString)
                {
                    if (escaped)
                        escaped = false;
                    else if (character == '\\')
                        escaped = true;
                    else if (character == '"')
                        inString = false;
                    continue;
                }

                if (character == '"')
                    inString = true;
                else if (character == '\'')
                    return true;
            }
            return false;
        }

        private static bool TryFindDuplicateProperty(string json, out string duplicatePath)
        {
            duplicatePath = "$";
            var objectMembers = new Stack<HashSet<string>>();
            try
            {
                using var textReader = new StringReader(json);
                using var reader = new JsonTextReader(textReader)
                {
                    Culture = CultureInfo.InvariantCulture,
                    DateParseHandling = DateParseHandling.None,
                    MaxDepth = 64,
                    SupportMultipleContent = true
                };
                while (reader.Read())
                {
                    if (reader.TokenType == JsonToken.StartObject)
                    {
                        objectMembers.Push(new HashSet<string>(StringComparer.Ordinal));
                    }
                    else if (reader.TokenType == JsonToken.EndObject)
                    {
                        if (objectMembers.Count > 0)
                            objectMembers.Pop();
                    }
                    else if (reader.TokenType == JsonToken.PropertyName && objectMembers.Count > 0)
                    {
                        var propertyName = Convert.ToString(reader.Value, CultureInfo.InvariantCulture);
                        if (!objectMembers.Peek().Add(propertyName))
                        {
                            duplicatePath = string.IsNullOrWhiteSpace(reader.Path) ? "$" : "$." + reader.Path;
                            return true;
                        }
                    }
                }
            }
            catch (JsonReaderException)
            {
                // Le parse principal rendra l'erreur syntaxique stable `json_invalid`.
            }
            return false;
        }

        private static TopologyParseResult Invalid(IReadOnlyList<TopologyIssue> issues)
        {
            return new TopologyParseResult(null, issues);
        }

        private static void Add(ICollection<TopologyIssue> issues, string code, string path, string message)
        {
            issues.Add(new TopologyIssue(code, path, message));
        }
    }
}
