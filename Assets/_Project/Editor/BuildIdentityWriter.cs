using System;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

namespace NotThatWay.Game.Editor
{
    public static class BuildIdentityWriter
    {
        private const string GeneratedDirectory = "Assets/_GeneratedLocal/Resources";
        private const string ResourcePath = GeneratedDirectory + "/GAMEBuildIdentity.json";

        private static readonly Regex CommitPattern =
            new Regex("^[0-9a-f]{40}$", RegexOptions.CultureInvariant);

        private static readonly Regex IdentifierPattern =
            new Regex("^[0-9a-f]{64}$", RegexOptions.CultureInvariant);

        public static BuildIdentityRecord WriteForBuild(string expectedProfile, string expectedPlatform)
        {
            var profile = ReadExpectedEnvironment("GAME_BUILD_PROFILE", expectedProfile);
            var platform = ReadExpectedEnvironment("GAME_BUILD_PLATFORM", expectedPlatform);
            var startedAtUtc = ReadEnvironment("GAME_BUILD_STARTED_AT_UTC") ??
                               DateTime.UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture);
            var unityVersion = ReadEnvironment("GAME_UNITY_VERSION") ?? Application.unityVersion;

            if (!string.Equals(unityVersion, Application.unityVersion, StringComparison.Ordinal))
            {
                throw new InvalidOperationException(
                    $"GAME_UNITY_VERSION={unityVersion} ne correspond pas a l'editeur {Application.unityVersion}.");
            }

            var commit = (ReadEnvironment("GAME_SOURCE_GIT_COMMIT") ?? "unknown").ToLowerInvariant();
            var dirty = ParseDirtyWorktree(ReadEnvironment("GAME_SOURCE_DIRTY_WORKTREE"));
            if (!CommitPattern.IsMatch(commit))
            {
                if (commit != "unknown")
                    throw new InvalidOperationException("GAME_SOURCE_GIT_COMMIT doit etre un SHA Git complet.");
                dirty = true;
            }

            var buildSetId = ReadEnvironment("GAME_BUILD_SET_ID") ?? Hash(
                $"schema=1|commit={commit}|dirty={dirty.ToString().ToLowerInvariant()}|" +
                $"profile={profile}|unity={unityVersion}|started={startedAtUtc}");
            var buildId = ReadEnvironment("GAME_BUILD_ID") ?? Hash($"{buildSetId}|platform={platform}");
            RequireIdentifier("GAME_BUILD_SET_ID", buildSetId);
            RequireIdentifier("GAME_BUILD_ID", buildId);

            var identity = new BuildIdentityRecord
            {
                schemaVersion = BuildIdentity.CurrentSchemaVersion,
                buildId = buildId,
                buildSetId = buildSetId,
                sourceGitCommit = commit,
                sourceDirtyWorktree = dirty,
                profile = profile,
                platform = platform,
                unityVersion = unityVersion,
                startedAtUtc = startedAtUtc
            };

            if (!BuildIdentity.Validate(identity, out var error))
                throw new InvalidOperationException($"Identite de build invalide: {error}.");

            Directory.CreateDirectory(GeneratedDirectory);
            File.WriteAllText(ResourcePath, JsonUtility.ToJson(identity, true) + "\n", new UTF8Encoding(false));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            AssetDatabase.ImportAsset(
                ResourcePath,
                ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);

            Debug.Log($"[GAME-BUILD] Embedded identity {identity.buildId} ({identity.buildSetId}).");
            return identity;
        }

        private static string ReadExpectedEnvironment(string name, string expected)
        {
            var normalizedExpected = expected.Trim().ToLowerInvariant();
            var value = (ReadEnvironment(name) ?? normalizedExpected).ToLowerInvariant();
            if (!string.Equals(value, normalizedExpected, StringComparison.Ordinal))
                throw new InvalidOperationException($"{name}={value} mais le build demande {normalizedExpected}.");
            return value;
        }

        private static string ReadEnvironment(string name)
        {
            var value = Environment.GetEnvironmentVariable(name);
            return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
        }

        private static bool ParseDirtyWorktree(string raw)
        {
            if (raw == null)
                return true;
            if (!bool.TryParse(raw, out var value))
                throw new InvalidOperationException("GAME_SOURCE_DIRTY_WORKTREE doit valoir true ou false.");
            return value;
        }

        private static void RequireIdentifier(string name, string value)
        {
            if (!IdentifierPattern.IsMatch(value))
                throw new InvalidOperationException($"{name} doit etre un SHA-256 hexadecimal.");
        }

        private static string Hash(string value)
        {
            using var algorithm = SHA256.Create();
            var bytes = algorithm.ComputeHash(Encoding.UTF8.GetBytes(value));
            var builder = new StringBuilder(bytes.Length * 2);
            foreach (var item in bytes)
                builder.Append(item.ToString("x2", CultureInfo.InvariantCulture));
            return builder.ToString();
        }
    }
}
