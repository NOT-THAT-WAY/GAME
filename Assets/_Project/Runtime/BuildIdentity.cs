using System;
using System.Globalization;
using System.Text.RegularExpressions;
using UnityEngine;

namespace NotThatWay.Game
{
    [Serializable]
    public sealed class BuildIdentityRecord
    {
        public int schemaVersion;
        public string buildId;
        public string buildSetId;
        public string sourceGitCommit;
        public bool sourceDirtyWorktree;
        public string profile;
        public string platform;
        public string unityVersion;
        public string startedAtUtc;
    }

    /// <summary>
    /// Identite immuable injectee dans chaque player au moment du build.
    /// Le marqueur loggue permet de relier une preuve reseau au binaire qui l'a produite,
    /// plutot qu'a un SHA fourni manuellement apres le test.
    /// </summary>
    public static class BuildIdentity
    {
        public const int CurrentSchemaVersion = 1;
        public const string ResourceName = "GAMEBuildIdentity";

        private static readonly Regex IdentifierPattern =
            new Regex("^[0-9a-f]{64}$", RegexOptions.CultureInvariant);

        private static readonly Regex CommitPattern =
            new Regex("^[0-9a-f]{40}$", RegexOptions.CultureInvariant);

        private static readonly Regex SlugPattern =
            new Regex("^[a-z0-9]+(?:-[a-z0-9]+)*$", RegexOptions.CultureInvariant);

        public static bool TryParse(string json, out BuildIdentityRecord identity, out string error)
        {
            identity = null;
            error = string.Empty;

            if (string.IsNullOrWhiteSpace(json))
            {
                error = "identity_json_empty";
                return false;
            }

            try
            {
                identity = JsonUtility.FromJson<BuildIdentityRecord>(json);
            }
            catch (ArgumentException)
            {
                error = "identity_json_invalid";
                return false;
            }

            return Validate(identity, out error);
        }

        public static bool Validate(BuildIdentityRecord identity, out string error)
        {
            if (identity == null)
                return Invalid("identity_missing", out error);
            if (identity.schemaVersion != CurrentSchemaVersion)
                return Invalid("identity_schema_unsupported", out error);
            if (!Matches(IdentifierPattern, identity.buildId))
                return Invalid("build_id_invalid", out error);
            if (!Matches(IdentifierPattern, identity.buildSetId))
                return Invalid("build_set_id_invalid", out error);
            if (!Matches(CommitPattern, identity.sourceGitCommit) &&
                !(identity.sourceGitCommit == "unknown" && identity.sourceDirtyWorktree))
            {
                return Invalid("source_commit_invalid", out error);
            }
            if (!Matches(SlugPattern, identity.profile))
                return Invalid("profile_invalid", out error);
            if (identity.platform != "macos" && identity.platform != "windows")
                return Invalid("platform_invalid", out error);
            if (string.IsNullOrWhiteSpace(identity.unityVersion) || HasWhitespace(identity.unityVersion))
                return Invalid("unity_version_invalid", out error);
            if (!DateTime.TryParseExact(
                    identity.startedAtUtc,
                    "yyyy-MM-dd'T'HH:mm:ss'Z'",
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                    out _))
            {
                return Invalid("started_at_utc_invalid", out error);
            }

            error = string.Empty;
            return true;
        }

        public static string FormatMarker(BuildIdentityRecord identity)
        {
            if (!Validate(identity, out var error))
                throw new ArgumentException($"Cannot format invalid build identity: {error}.", nameof(identity));

            return string.Concat(
                "[GAME-BUILD] schema=", identity.schemaVersion,
                " buildId=", identity.buildId,
                " buildSetId=", identity.buildSetId,
                " commit=", identity.sourceGitCommit,
                " dirty=", identity.sourceDirtyWorktree ? "true" : "false",
                " profile=", identity.profile,
                " platform=", identity.platform,
                " unity=", identity.unityVersion,
                " startedAt=", identity.startedAtUtc);
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void AnnounceBuildIdentity()
        {
            var asset = Resources.Load<TextAsset>(ResourceName);
            if (asset == null)
            {
                // Seul un player construit par le pipeline possède une identité
                // injectée. En éditeur, son absence est l'état normal : une
                // erreur ici ferait passer chaque session Play pour un build
                // invalide et noierait les vraies erreurs du banc.
                if (Application.isEditor)
                {
                    Debug.Log("[GAME-BUILD] editor_session identity=none");
                    return;
                }
                Debug.LogError("[GAME-BUILD] invalid reason=identity_resource_missing");
                return;
            }

            if (!TryParse(asset.text, out var identity, out var error))
            {
                Debug.LogError($"[GAME-BUILD] invalid reason={error}");
                return;
            }

            Debug.Log(FormatMarker(identity));
        }

        private static bool Matches(Regex pattern, string value)
        {
            return value != null && pattern.IsMatch(value);
        }

        private static bool HasWhitespace(string value)
        {
            foreach (var character in value)
            {
                if (char.IsWhiteSpace(character))
                    return true;
            }

            return false;
        }

        private static bool Invalid(string reason, out string error)
        {
            error = reason;
            return false;
        }
    }
}
