using System;

namespace NotThatWay.Game.Sandbox
{
    public enum SandboxCarryableKind : byte
    {
        None = 0,
        Rock = 1,
        Trophy = 2,
        Slingshot = 3,
        OilCan = 4
    }

    public enum SandboxCarryablePhase : byte
    {
        World = 0,
        Held = 1,
        Thrown = 2,
        Deposited = 3
    }

    public readonly struct SandboxInventoryEntry : IEquatable<SandboxInventoryEntry>
    {
        public SandboxInventoryEntry(int objectId, SandboxCarryableKind kind)
        {
            if (objectId < 0)
                throw new ArgumentOutOfRangeException(nameof(objectId));
            if (kind == SandboxCarryableKind.None)
                throw new ArgumentOutOfRangeException(nameof(kind));
            ObjectId = objectId;
            Kind = kind;
        }

        public int ObjectId { get; }
        public SandboxCarryableKind Kind { get; }
        public bool IsEmpty => Kind == SandboxCarryableKind.None;
        public bool Equals(SandboxInventoryEntry other) =>
            ObjectId == other.ObjectId && Kind == other.Kind;
        public override bool Equals(object value) =>
            value is SandboxInventoryEntry other && Equals(other);
        public override int GetHashCode() => HashCode.Combine(ObjectId, Kind);
    }

    /// <summary>Inventaire pur à trois cases, sans stack ni poids implicite.</summary>
    public sealed class SandboxInventoryModel
    {
        public const int Capacity = 3;

        private readonly SandboxInventoryEntry?[] _slots =
            new SandboxInventoryEntry?[Capacity];
        private int _activeSlot;

        public int ActiveSlot => _activeSlot;
        public int Count { get; private set; }
        public bool IsFull => Count == Capacity;
        public bool HasTrophy
        {
            get
            {
                for (var index = 0; index < Capacity; index++)
                {
                    if (_slots[index]?.Kind == SandboxCarryableKind.Trophy)
                        return true;
                }
                return false;
            }
        }

        public SandboxInventoryEntry? ActiveEntry => _slots[_activeSlot];

        public bool HasKind(SandboxCarryableKind kind) => TryFindFirstOfKind(kind, out _);

        /// <summary>Case de la première occurrence du genre, ou -1.</summary>
        public int IndexOfKind(SandboxCarryableKind kind)
        {
            for (var index = 0; index < Capacity; index++)
            {
                if (_slots[index]?.Kind == kind)
                    return index;
            }
            return -1;
        }

        /// <summary>Première case, par ordre de case, qui contient un objet du genre demandé.</summary>
        public bool TryFindFirstOfKind(SandboxCarryableKind kind, out SandboxInventoryEntry entry)
        {
            for (var index = 0; index < Capacity; index++)
            {
                var value = _slots[index];
                if (!value.HasValue || value.Value.Kind != kind)
                    continue;
                entry = value.Value;
                return true;
            }
            entry = default;
            return false;
        }

        public SandboxInventoryEntry? EntryAt(int slot)
        {
            ValidateSlot(slot);
            return _slots[slot];
        }

        public bool TryAdd(SandboxInventoryEntry entry, out int slot)
        {
            if (ContainsObject(entry.ObjectId) || IsFull)
            {
                slot = -1;
                return false;
            }

            for (var index = 0; index < Capacity; index++)
            {
                if (_slots[index].HasValue)
                    continue;
                _slots[index] = entry;
                _activeSlot = index;
                Count++;
                slot = index;
                return true;
            }

            slot = -1;
            return false;
        }

        public bool Select(int slot)
        {
            ValidateSlot(slot);
            _activeSlot = slot;
            return true;
        }

        public bool TryRemoveActive(out SandboxInventoryEntry entry)
        {
            var value = _slots[_activeSlot];
            if (!value.HasValue)
            {
                entry = default;
                return false;
            }

            entry = value.Value;
            _slots[_activeSlot] = null;
            Count--;
            SelectNextOccupied();
            return true;
        }

        public bool TryRemoveObject(int objectId, out SandboxInventoryEntry entry)
        {
            for (var index = 0; index < Capacity; index++)
            {
                var value = _slots[index];
                if (!value.HasValue || value.Value.ObjectId != objectId)
                    continue;
                entry = value.Value;
                _slots[index] = null;
                Count--;
                if (_activeSlot == index)
                    SelectNextOccupied();
                return true;
            }
            entry = default;
            return false;
        }

        public bool TryRemoveAny(out SandboxInventoryEntry entry)
        {
            for (var slot = 0; slot < Capacity; slot++)
            {
                var value = _slots[slot];
                if (!value.HasValue)
                    continue;
                return TryRemoveObject(value.Value.ObjectId, out entry);
            }
            entry = default;
            return false;
        }

        public void Clear()
        {
            Array.Clear(_slots, 0, _slots.Length);
            _activeSlot = 0;
            Count = 0;
        }

        private bool ContainsObject(int objectId)
        {
            for (var index = 0; index < Capacity; index++)
            {
                if (_slots[index]?.ObjectId == objectId)
                    return true;
            }
            return false;
        }

        private void SelectNextOccupied()
        {
            for (var offset = 1; offset <= Capacity; offset++)
            {
                var candidate = (_activeSlot + offset) % Capacity;
                if (!_slots[candidate].HasValue)
                    continue;
                _activeSlot = candidate;
                return;
            }
            _activeSlot = 0;
        }

        private static void ValidateSlot(int slot)
        {
            if (slot < 0 || slot >= Capacity)
                throw new ArgumentOutOfRangeException(nameof(slot));
        }
    }
}
