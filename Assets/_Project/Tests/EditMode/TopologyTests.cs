using System.Globalization;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using NotThatWay.Game.Topology;
using NUnit.Framework;

namespace NotThatWay.Game.Tests.EditMode
{
    public sealed class TopologyTests
    {
        private const string FixtureDirectory = "Assets/_Project/Tests/Fixtures/Topology";

        [Test]
        public void ValidFixture_ParsesAndProducesStableCanonicalBytes()
        {
            var result = ParseFixture("valid-minimal.json");

            Assert.That(result.IsValid, Is.True, FormatIssues(result));
            Assert.That(result.Document.TopologyId, Is.EqualTo("fixture-valid-minimal"));
            Assert.That(result.Document.Walls.Select(wall => wall.WallId), Is.EqualTo(new[] { 10 }));
            Assert.That(result.Document.Pivots.Select(pivot => pivot.PivotId), Is.EqualTo(new[] { 100 }));

            var checksum = TopologyCanonicalizer.ComputeChecksum(result.Document);
            Assert.That(checksum, Is.EqualTo("b78a1da881f0e53318a308a04f08217a07cad57412522870fd10bca76008e580"));

            result.Document.Openings.Reverse();
            result.Document.Spawns.Reverse();
            result.Document.Walls[0].States.Reverse();
            Assert.That(TopologyCanonicalizer.ComputeChecksum(result.Document), Is.EqualTo(checksum));
        }

        [TestCase("invalid-unsupported-schema-version.json", TopologyIssueCodes.SchemaVersionUnsupported)]
        [TestCase("invalid-duplicate-wall-id.json", TopologyIssueCodes.WallIdDuplicate)]
        [TestCase("invalid-broken-pivot-reference.json", TopologyIssueCodes.PivotReferenceMissing)]
        [TestCase("invalid-edge-out-of-bounds.json", TopologyIssueCodes.EdgeOutOfBounds)]
        [TestCase("invalid-spawn-out-of-bounds.json", TopologyIssueCodes.SpawnOutOfBounds)]
        [TestCase("invalid-duplicate-json-property.json", TopologyIssueCodes.JsonPropertyDuplicate)]
        [TestCase("invalid-unknown-json-member.json", TopologyIssueCodes.JsonMemberUnknown)]
        public void InvalidFixture_IsRejectedWithoutPartialDocument(string fileName, string expectedCode)
        {
            var result = ParseFixture(fileName);

            Assert.That(result.IsValid, Is.False);
            Assert.That(result.Document, Is.Null);
            Assert.That(result.Issues.Select(issue => issue.Code).Distinct(), Is.EqualTo(new[] { expectedCode }));
        }

        [Test]
        public void DeclaredChecksum_MustMatchCanonicalContent()
        {
            var source = File.ReadAllText(Path.Combine(FixtureDirectory, "valid-minimal.json"));
            var parsed = TopologyParser.Parse(source);
            Assert.That(parsed.IsValid, Is.True, FormatIssues(parsed));
            var checksum = TopologyCanonicalizer.ComputeChecksum(parsed.Document);
            var withChecksum = WithChecksum(source, checksum);

            Assert.That(TopologyParser.ParseVerified(withChecksum).IsValid, Is.True);

            var tampered = withChecksum.Replace(checksum, new string('0', 64));
            var rejected = TopologyParser.ParseVerified(tampered);
            Assert.That(rejected.IsValid, Is.False);
            Assert.That(rejected.Issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.ChecksumMismatch));
        }

        [Test]
        public void Migrated16x16Topology_IsValidAndReproduciblyIdentified()
        {
            var path = "Assets/_Project/Maze/MazeTopology16x16.v1.json";
            var result = TopologyParser.ParseVerified(File.ReadAllText(path));

            Assert.That(result.IsValid, Is.True, FormatIssues(result));
            Assert.That(result.Document.Dimensions.WidthCells, Is.EqualTo(16));
            Assert.That(result.Document.Dimensions.HeightCells, Is.EqualTo(16));
            Assert.That(result.Document.Walls, Has.Count.EqualTo(279));
            Assert.That(result.Document.Pivots, Has.Count.EqualTo(17));
            Assert.That(result.Document.Openings, Has.Count.EqualTo(4));
            Assert.That(result.Document.Spawns, Has.Count.EqualTo(4));
            Assert.That(
                result.Document.Checksum,
                Is.EqualTo("36a81a05cfe75d751f6fa4c25f105060116b8c6fba0816d811b552baed3e528a"));
            Assert.That(TopologyCanonicalizer.ComputeChecksum(result.Document), Is.EqualTo(result.Document.Checksum));
        }

        [Test]
        public void CanonicalChecksum_IsIndependentOfLineEndingsAndCurrentCulture()
        {
            var source = File.ReadAllText(Path.Combine(FixtureDirectory, "valid-minimal.json"));
            var lf = TopologyParser.Parse(source.Replace("\r\n", "\n"));
            var crlf = TopologyParser.Parse(source.Replace("\r\n", "\n").Replace("\n", "\r\n"));
            Assert.That(lf.IsValid, Is.True, FormatIssues(lf));
            Assert.That(crlf.IsValid, Is.True, FormatIssues(crlf));

            var previousCulture = CultureInfo.CurrentCulture;
            try
            {
                CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("fr-BE");
                var frenchChecksum = TopologyCanonicalizer.ComputeChecksum(lf.Document);
                CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("en-US");
                var englishChecksum = TopologyCanonicalizer.ComputeChecksum(crlf.Document);
                Assert.That(englishChecksum, Is.EqualTo(frenchChecksum));
            }
            finally
            {
                CultureInfo.CurrentCulture = previousCulture;
            }
        }

        [Test]
        public void VerifiedParse_RequiresANonEmptyChecksum()
        {
            var source = File.ReadAllText(Path.Combine(FixtureDirectory, "valid-minimal.json"));

            var missing = TopologyParser.ParseVerified(source);
            var empty = TopologyParser.ParseVerified(WithChecksum(source, string.Empty));

            Assert.That(missing.IsValid, Is.False);
            Assert.That(missing.Issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.ChecksumRequired));
            Assert.That(empty.IsValid, Is.False);
            Assert.That(empty.Issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.ChecksumRequired));
        }

        [Test]
        public void StrictJson_RejectsExtensionsAndOversizedPayloads()
        {
            var source = File.ReadAllText(Path.Combine(FixtureDirectory, "valid-minimal.json"));
            var commented = source.Replace("{\n", "{\n  /* forbidden */\n");
            var trimmed = source.TrimEnd();
            var trailingComma = trimmed.Substring(0, trimmed.Length - 1) + ",\n}";
            const string singleQuoted = "{'schemaVersion':1}";
            var hexadecimal = source.Replace("\"schemaVersion\": 1", "\"schemaVersion\": 0x1");
            var oversized = source + new string(' ', TopologyParser.MaximumJsonBytes);

            var commentResult = TopologyParser.Parse(commented);
            var commaResult = TopologyParser.Parse(trailingComma);
            var singleQuoteResult = TopologyParser.Parse(singleQuoted);
            var hexadecimalResult = TopologyParser.Parse(hexadecimal);
            var oversizedResult = TopologyParser.Parse(oversized);

            Assert.That(commentResult.IsValid, Is.False);
            Assert.That(
                commentResult.Issues.Select(issue => issue.Code),
                Does.Contain(TopologyIssueCodes.JsonCommentForbidden));
            Assert.That(commaResult.IsValid, Is.False);
            Assert.That(commaResult.Issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.JsonInvalid));
            Assert.That(singleQuoteResult.IsValid, Is.False);
            Assert.That(singleQuoteResult.Issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.JsonInvalid));
            Assert.That(hexadecimalResult.IsValid, Is.False);
            Assert.That(hexadecimalResult.Issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.JsonInvalid));
            Assert.That(oversizedResult.IsValid, Is.False);
            Assert.That(oversizedResult.Issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.JsonTooLarge));
        }

        [Test]
        public void PivotAndWallReferences_MustBeReciprocal()
        {
            var document = ParseValidDocument();
            document.Pivots.Add(
                new TopologyPivot
                {
                    PivotId = 101,
                    Node = new TopologyPoint { X = 1, Y = 0 },
                    WallIds = new List<int> { 10 }
                });

            var issues = TopologyValidator.Validate(document);

            Assert.That(issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.WallPivotMismatch));
        }

        [Test]
        public void WallStates_MustHaveUniqueCoherentPoses()
        {
            var document = ParseValidDocument();
            var first = document.Walls[0].States[0];
            var second = document.Walls[0].States[1];
            second.Edge = new TopologyEdge { Axis = first.Edge.Axis, X = first.Edge.X, Y = first.Edge.Y };
            second.QuarterTurns = first.QuarterTurns;

            var issues = TopologyValidator.Validate(document);
            var codes = issues.Select(issue => issue.Code).ToArray();

            Assert.That(codes, Does.Contain(TopologyIssueCodes.WallStateEdgeDuplicate));
            Assert.That(codes, Does.Contain(TopologyIssueCodes.QuarterTurnsDuplicate));
        }

        [Test]
        public void WallStateRotation_MustMatchItsDeclaredQuarterTurns()
        {
            var document = ParseValidDocument();
            document.Walls[0].States[1].QuarterTurns = 2;

            var issues = TopologyValidator.Validate(document);

            Assert.That(
                issues.Select(issue => issue.Code),
                Does.Contain(TopologyIssueCodes.WallStateRotationMismatch));
        }

        [Test]
        public void InitialEdgesAndOpenings_CannotOverlap()
        {
            var document = ParseValidDocument();
            var edge = document.Walls[0].States[0].Edge;
            document.Openings[0].Edge = new TopologyEdge { Axis = edge.Axis, X = edge.X, Y = edge.Y };
            document.Walls.Add(
                new TopologyWall
                {
                    WallId = 11,
                    InitialStateId = 0,
                    States = new List<TopologyWallState>
                    {
                        new()
                        {
                            StateId = 0,
                            Edge = new TopologyEdge { Axis = edge.Axis, X = edge.X, Y = edge.Y },
                            QuarterTurns = 0
                        }
                    }
                });

            var issues = TopologyValidator.Validate(document);
            var codes = issues.Select(issue => issue.Code).ToArray();

            Assert.That(codes, Does.Contain(TopologyIssueCodes.InitialEdgeDuplicate));
            Assert.That(codes, Does.Contain(TopologyIssueCodes.OpeningOverlapsWall));
        }

        [Test]
        public void RuntimeTopology_RequiresAtLeastTwoPosesForMobileWalls()
        {
            var document = ParseValidDocument();
            document.Walls[0].States.RemoveAt(1);

            var issues = TopologyValidator.ValidateForRuntime(document);

            Assert.That(issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.WallStateCountInvalid));
        }

        [Test]
        public void Dimensions_RejectPhysicalMetricsBeyondTheRuntimeContract()
        {
            var document = ParseValidDocument();
            document.Dimensions.CellPitchMm = int.MaxValue;

            var issues = TopologyValidator.Validate(document);

            Assert.That(issues.Select(issue => issue.Code), Does.Contain(TopologyIssueCodes.DimensionsInvalid));
        }

        private static TopologyParseResult ParseFixture(string fileName)
        {
            return TopologyParser.Parse(File.ReadAllText(Path.Combine(FixtureDirectory, fileName)));
        }

        private static TopologyDocument ParseValidDocument()
        {
            var result = ParseFixture("valid-minimal.json");
            Assert.That(result.IsValid, Is.True, FormatIssues(result));
            return result.Document;
        }

        private static string WithChecksum(string source, string checksum)
        {
            var trimmed = source.TrimEnd();
            return trimmed.Substring(0, trimmed.Length - 1) +
                   $",\n  \"checksum\": \"{checksum}\"\n}}";
        }

        private static string FormatIssues(TopologyParseResult result)
        {
            return string.Join(", ", result.Issues.Select(issue => $"{issue.Code}@{issue.Path}"));
        }
    }
}
