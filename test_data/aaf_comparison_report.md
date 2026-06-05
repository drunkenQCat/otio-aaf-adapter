# AAF Multi-Track Structural Comparison Report

- **Correct**: `test_data/飞驰人生测试_20260515.20260602163810.aaf`
- **Ours**: `test_data/飞驰人生测试_testdata.aaf`
- **Date**: 2026-06-02

---

## 1. Header Differences

| Property | Correct | Ours | Match? |
|----------|---------|------|--------|
| Version | {'major': 1, 'minor': 1} | {'major': 1, 'minor': 1} | ✅ |
| ObjectModelVersion | 1 | 1 | ✅ |
| ByteOrder | 0x4949 | 0x4949 | ✅ |
| OperationalPattern | None | None | ✅ |

### Identification[0]

| Property | Correct | Ours | Match? |
|----------|---------|------|--------|
| CompanyName | 'Blackmagic Design' | 'Blackmagic Design' | ✅ |
| ProductName | 'DaVinci Resolve' | 'DaVinci Resolve' | ✅ |
| ProductVersionString | 'Unknown version' | 'Unknown version' | ✅ |
| ProductVersion | {'major': 19, 'minor': 0, 'tertiary': 0, 'patchLevel': 0, 'type': 'VersionReleased'} | {'major': 19, 'minor': 0, 'tertiary': 0, 'patchLevel': 0, 'type': 'VersionReleased'} | ✅ |
| ToolkitVersion | {'major': 1, 'minor': 1, 'tertiary': 6, 'patchLevel': 0, 'type': 'VersionReleased'} | {'major': 1, 'minor': 1, 'tertiary': 6, 'patchLevel': 0, 'type': 'VersionReleased'} | ✅ |

---

## 2. Mob Overview

| Metric | Correct | Ours | Match? |
|--------|---------|------|--------|
| Total Mobs | 73 | 73 | ✅ |
| CompositionMob | 1 | 1 | ✅ |
| MasterMob | 24 | 24 | ✅ |
| SourceMob | 48 | 48 | ✅ |

### Mob Type Sequence

- **Correct**: `['CompositionMob', 'MasterMob', 'SourceMob', 'SourceMob', 'MasterMob', 'SourceMob', 'SourceMob', 'MasterMob', 'SourceMob', 'SourceMob']...` (showing first 10)
- **Ours**: `['CompositionMob', 'MasterMob', 'SourceMob', 'SourceMob', 'MasterMob', 'SourceMob', 'SourceMob', 'MasterMob', 'SourceMob', 'SourceMob']...` (showing first 10)
- **Match**: ✅

---

## 3. CompositionMob

| Property | Correct | Ours | Match? |
|----------|---------|------|--------|
| Name | '飞驰人生测试_20260515' | '飞驰人生测试_20260515' | ✅ |
| Slots | 5 | 5 | ✅ |

### Slot Summary

| SlotID | Rate | Name | PTN | SegType | Length | Match? |
|--------|------|------|-----|---------|--------|--------|
| 1 | 24 | '' | 1 | Timecode | 16932 | ✅ |
| 3 | 48000 | '叶经理_1' | 1 | Sequence | 33864000 | ✅ |
| 4 | 48000 | '叶经理_2' | 2 | Sequence | 33864000 | ✅ |
| 5 | 48000 | '叶经理_3' | 3 | Sequence | 33864000 | ✅ |
| 6 | 48000 | '叶经理_4' | 4 | Sequence | 33864000 | ✅ |

### Timecode Slot

| Property | Correct | Ours | Match? |
|----------|---------|------|--------|
| start | 0 | 0 | ✅ |
| fps | 24 | 24 | ✅ |
| length | 16932 | 16932 | ✅ |

### Audio Slot Component Comparison

#### Slot[3] '叶经理_1'

- Correct: 19 components
- Ours: 19 components
- Match: ✅

| # | Correct Type | Correct Len | Ours Type | Ours Len | Len Match? |
|---|-------------|------------|-----------|---------|-----------|
| 0 | Filler | 28524000 | Filler | 28524000 | ✅ |
| 1 | OperationGroup | 476000 | SourceClip | 477023 | ❌ |
| 2 | Filler | 1026000 | Filler | 1024976 | ❌ |
| 3 | OperationGroup | 352000 | SourceClip | 352175 | ❌ |
| 4 | Filler | 296000 | Filler | 295824 | ❌ |
| 5 | OperationGroup | 384000 | SourceClip | 384480 | ❌ |
| 6 | Filler | 20000 | Filler | 19519 | ❌ |
| 7 | OperationGroup | 294000 | SourceClip | 295727 | ❌ |
| 8 | Filler | 120000 | Filler | 118272 | ❌ |
| 9 | OperationGroup | 512000 | SourceClip | 513743 | ❌ |
| 10 | Filler | 88000 | Filler | 86256 | ❌ |
| 11 | OperationGroup | 214000 | SourceClip | 214560 | ❌ |
| 12 | Filler | 26000 | Filler | 25439 | ❌ |
| 13 | OperationGroup | 320000 | SourceClip | 320927 | ❌ |
| 14 | Filler | 74000 | Filler | 73072 | ❌ |
| 15 | OperationGroup | 352000 | SourceClip | 352175 | ❌ |
| 16 | Filler | 468000 | Filler | 467824 | ❌ |
| 17 | OperationGroup | 316000 | SourceClip | 317039 | ❌ |
| 18 | Filler | 2000 | Filler | 969 | ❌ |

**OperationGroup Details (Correct):**

| # | Op Name | Inputs | Params | Input Types |
|---|---------|--------|--------|-------------|
| 0 | Audio Gain | 1 | 1 | SourceClip |
| 1 | Audio Gain | 1 | 1 | SourceClip |
| 2 | Audio Gain | 1 | 1 | SourceClip |
| 3 | Audio Gain | 1 | 1 | SourceClip |
| 4 | Audio Gain | 1 | 1 | SourceClip |
| 5 | Audio Gain | 1 | 1 | SourceClip |
| 6 | Audio Gain | 1 | 1 | SourceClip |
| 7 | Audio Gain | 1 | 1 | SourceClip |
| 8 | Audio Gain | 1 | 1 | SourceClip |

**First OperationGroup Parameters:**

- Type: `ConstantValue`, Name: `None`, Value: `536870912/536870912`

#### Slot[4] '叶经理_2'

- Correct: 17 components
- Ours: 17 components
- Match: ✅

| # | Correct Type | Correct Len | Ours Type | Ours Len | Len Match? |
|---|-------------|------------|-----------|---------|-----------|
| 0 | Filler | 30138000 | Filler | 30137999 | ❌ |
| 1 | OperationGroup | 176000 | SourceClip | 177743 | ❌ |
| 2 | Filler | 2000 | Filler | 256 | ❌ |
| 3 | OperationGroup | 176000 | SourceClip | 177743 | ❌ |
| 4 | Filler | 222000 | Filler | 220255 | ❌ |
| 5 | OperationGroup | 196000 | SourceClip | 197663 | ❌ |
| 6 | Filler | 46000 | Filler | 44337 | ❌ |
| 7 | OperationGroup | 252000 | SourceClip | 253535 | ❌ |
| 8 | Filler | 152000 | Filler | 150464 | ❌ |
| 9 | OperationGroup | 202000 | SourceClip | 202223 | ❌ |
| 10 | Filler | 56000 | Filler | 55775 | ❌ |
| 11 | OperationGroup | 330000 | SourceClip | 331535 | ❌ |
| 12 | Filler | 40000 | Filler | 38465 | ❌ |
| 13 | OperationGroup | 270000 | SourceClip | 270240 | ❌ |
| 14 | Filler | 236000 | Filler | 235759 | ❌ |
| 15 | OperationGroup | 172000 | SourceClip | 173807 | ❌ |
| 16 | Filler | 1198000 | Filler | 1196201 | ❌ |

**OperationGroup Details (Correct):**

| # | Op Name | Inputs | Params | Input Types |
|---|---------|--------|--------|-------------|
| 0 | Audio Gain | 1 | 1 | SourceClip |
| 1 | Audio Gain | 1 | 1 | SourceClip |
| 2 | Audio Gain | 1 | 1 | SourceClip |
| 3 | Audio Gain | 1 | 1 | SourceClip |
| 4 | Audio Gain | 1 | 1 | SourceClip |
| 5 | Audio Gain | 1 | 1 | SourceClip |
| 6 | Audio Gain | 1 | 1 | SourceClip |
| 7 | Audio Gain | 1 | 1 | SourceClip |

**First OperationGroup Parameters:**

- Type: `ConstantValue`, Name: `None`, Value: `536870912/536870912`

#### Slot[5] '叶经理_3'

- Correct: 11 components
- Ours: 11 components
- Match: ✅

| # | Correct Type | Correct Len | Ours Type | Ours Len | Len Match? |
|---|-------------|------------|-----------|---------|-----------|
| 0 | Filler | 30206000 | Filler | 30205999 | ❌ |
| 1 | OperationGroup | 398000 | SourceClip | 398975 | ❌ |
| 2 | Filler | 388000 | Filler | 387024 | ❌ |
| 3 | OperationGroup | 204000 | SourceClip | 204480 | ❌ |
| 4 | Filler | 536000 | Filler | 535520 | ❌ |
| 5 | OperationGroup | 452000 | SourceClip | 452447 | ❌ |
| 6 | Filler | 50000 | Filler | 49552 | ❌ |
| 7 | OperationGroup | 244000 | SourceClip | 245760 | ❌ |
| 8 | Filler | 86000 | Filler | 84240 | ❌ |
| 9 | OperationGroup | 274000 | SourceClip | 274127 | ❌ |
| 10 | Filler | 1026000 | Filler | 1025876 | ❌ |

**OperationGroup Details (Correct):**

| # | Op Name | Inputs | Params | Input Types |
|---|---------|--------|--------|-------------|
| 0 | Audio Gain | 1 | 1 | SourceClip |
| 1 | Audio Gain | 1 | 1 | SourceClip |
| 2 | Audio Gain | 1 | 1 | SourceClip |
| 3 | Audio Gain | 1 | 1 | SourceClip |
| 4 | Audio Gain | 1 | 1 | SourceClip |

**First OperationGroup Parameters:**

- Type: `ConstantValue`, Name: `None`, Value: `536870912/536870912`

#### Slot[6] '叶经理_4'

- Correct: 5 components
- Ours: 5 components
- Match: ✅

| # | Correct Type | Correct Len | Ours Type | Ours Len | Len Match? |
|---|-------------|------------|-----------|---------|-----------|
| 0 | Filler | 31828000 | Filler | 31828000 | ✅ |
| 1 | OperationGroup | 172000 | SourceClip | 173807 | ❌ |
| 2 | Filler | 168000 | Filler | 166192 | ❌ |
| 3 | OperationGroup | 378000 | SourceClip | 379007 | ❌ |
| 4 | Filler | 1318000 | Filler | 1316994 | ❌ |

**OperationGroup Details (Correct):**

| # | Op Name | Inputs | Params | Input Types |
|---|---------|--------|--------|-------------|
| 0 | Audio Gain | 1 | 1 | SourceClip |
| 1 | Audio Gain | 1 | 1 | SourceClip |

**First OperationGroup Parameters:**

- Type: `ConstantValue`, Name: `None`, Value: `536870912/536870912`

---

## 4. MasterMob

- Correct: 24 MasterMobs
- Ours: 24 MasterMobs

| # | Correct Name | Ours Name | Name Match? | Correct Slots | Ours Slots | Slots Match? |
|---|-------------|-----------|-------------|--------------|-----------|-------------|
| 0 | 'A1-0001_01_叶经理_rate1' | 'A1-0001_01_叶经理_rate1.0_260515_10PM_69e9_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 1 | 'A1-0002_05_叶经理_rate1' | 'A1-0002_05_叶经理_rate1.0_260515_10PM_2a09_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 2 | 'A2-0001_06_叶经理_rate1' | 'A1-0003_11_叶经理_rate1.0_260515_10PM_cb7b_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 3 | 'A3-0001_07_叶经理_rate1' | 'A1-0004_15_叶经理_rate1.0_260515_10PM_69f1_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 4 | 'A2-0002_08_叶经理_rate1' | 'A1-0005_19_叶经理_rate1.0_260515_10PM_6c87_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 5 | 'A1-0003_11_叶经理_rate1' | 'A1-0006_24_叶经理_rate1.0_260515_10PM_0e5a_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 6 | 'A2-0003_12_叶经理_rate1' | 'A1-0007_27_叶经理_rate1.0_260515_10PM_5e94_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 7 | 'A2-0004_13_叶经理_rate1' | 'A1-0008_30_叶经理_rate1.0_260515_10PM_9748_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 8 | 'A3-0002_14_叶经理_rate1' | 'A1-0009_37_叶经理_rate1.0_260515_10PM_09dd_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 9 | 'A1-0004_15_叶经理_rate1' | 'A2-0001_06_叶经理_rate1.0_260515_10PM_5e2c_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 10 | 'A2-0005_18_叶经理_rate1' | 'A2-0002_08_叶经理_rate1.0_260515_10PM_ef0e_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 11 | 'A1-0005_19_叶经理_rate1' | 'A2-0003_12_叶经理_rate1.0_260515_10PM_4325_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 12 | 'A2-0006_20_叶经理_rate1' | 'A2-0004_13_叶经理_rate1.0_260515_10PM_a132_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 13 | 'A3-0003_21_叶经理_rate1' | 'A2-0005_18_叶经理_rate1.0_260515_10PM_a522_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 14 | 'A4-0001_22_叶经理_rate1' | 'A2-0006_20_叶经理_rate1.0_260515_10PM_c63d_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 15 | 'A2-0007_23_叶经理_rate1' | 'A2-0007_23_叶经理_rate1.0_260515_10PM_4bed_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 16 | 'A1-0006_24_叶经理_rate1' | 'A2-0008_28_叶经理_rate1.0_260515_10PM_56c6_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 17 | 'A4-0002_25_叶经理_rate1' | 'A3-0001_07_叶经理_rate1.0_260515_10PM_f514_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 18 | 'A3-0004_26_叶经理_rate1' | 'A3-0002_14_叶经理_rate1.0_260515_10PM_614a_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 19 | 'A1-0007_27_叶经理_rate1' | 'A3-0003_21_叶经理_rate1.0_260515_10PM_fbf8_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 20 | 'A2-0008_28_叶经理_rate1' | 'A3-0004_26_叶经理_rate1.0_260515_10PM_d28d_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 21 | 'A3-0005_29_叶经理_rate1' | 'A3-0005_29_叶经理_rate1.0_260515_10PM_80e9_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 22 | 'A1-0008_30_叶经理_rate1' | 'A4-0001_22_叶经理_rate1.0_260515_10PM_c767_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |
| 23 | 'A1-0009_37_叶经理_rate1' | 'A4-0002_25_叶经理_rate1.0_260515_10PM_3f1c_MiniMax_SJH' | ❌ | 1 | 1 | ✅ |

### MasterMob PhysicalTrackNumber

| # | Correct PTN | Ours PTN | Match? |
|---|------------|---------|--------|
| 0 | 1 | 1 | ✅ |
| 1 | 1 | 1 | ✅ |
| 2 | 1 | 1 | ✅ |
| 3 | 1 | 1 | ✅ |
| 4 | 1 | 1 | ✅ |
| 5 | 1 | 1 | ✅ |
| 6 | 1 | 1 | ✅ |
| 7 | 1 | 1 | ✅ |
| 8 | 1 | 1 | ✅ |
| 9 | 1 | 1 | ✅ |
| 10 | 1 | 1 | ✅ |
| 11 | 1 | 1 | ✅ |
| 12 | 1 | 1 | ✅ |
| 13 | 1 | 1 | ✅ |
| 14 | 1 | 1 | ✅ |
| 15 | 1 | 1 | ✅ |
| 16 | 1 | 1 | ✅ |
| 17 | 1 | 1 | ✅ |
| 18 | 1 | 1 | ✅ |
| 19 | 1 | 1 | ✅ |
| 20 | 1 | 1 | ✅ |
| 21 | 1 | 1 | ✅ |
| 22 | 1 | 1 | ✅ |
| 23 | 1 | 1 | ✅ |

---

## 5. SourceMob

- Correct: 48 SourceMobs
- Ours: 48 SourceMobs

| Descriptor Type | Correct | Ours | Match? |
|----------------|---------|------|--------|
| TapeDescriptor | 24 | 24 | ✅ |
| WAVEDescriptor | 24 | 24 | ✅ |

### WAVEDescriptor Summary (first 3)

| # | Property | Correct | Ours | Match? |
|---|----------|---------|------|--------|
| [0] sample_rate | 48000 | 48000 | ✅ |
| [0] byte_rate | 144000 | 144000 | ✅ |
| [0] block_align | 3 | 3 | ✅ |
| [0] bits_per_sample | 24 | 24 | ✅ |
| [0] riff_size | 1428962 | 1428962 | ✅ |
| [0] data_size | 1428000 | 1428000 | ✅ |
| [0] locator_url | file:///C:/TechProjects/Timeline_Projects/otio-aaf-adapter/t... | file:///C:/TechProjects/Timeline_Projects/otio-aaf-adapter/t... | — |
| [1] sample_rate | 48000 | 48000 | ✅ |
| [1] byte_rate | 144000 | 144000 | ✅ |
| [1] block_align | 3 | 3 | ✅ |
| [1] bits_per_sample | 24 | 24 | ✅ |
| [1] riff_size | 1056962 | 1056962 | ✅ |
| [1] data_size | 1056000 | 1056000 | ✅ |
| [1] locator_url | file:///C:/TechProjects/Timeline_Projects/otio-aaf-adapter/t... | file:///C:/TechProjects/Timeline_Projects/otio-aaf-adapter/t... | — |
| [2] sample_rate | 48000 | 48000 | ✅ |
| [2] byte_rate | 144000 | 144000 | ✅ |
| [2] block_align | 3 | 3 | ✅ |
| [2] bits_per_sample | 24 | 24 | ✅ |
| [2] riff_size | 528962 | 1152962 | ❌ |
| [2] data_size | 528000 | 1152000 | ❌ |
| [2] locator_url | file:///C:/TechProjects/Timeline_Projects/otio-aaf-adapter/t... | file:///C:/TechProjects/Timeline_Projects/otio-aaf-adapter/t... | — |

---

## 6. Clip Length Precision Analysis

Comparing SourceClip lengths in CompositionMob audio sequences.

| Slot | Clip # | Correct Len | Ours Len | Diff | Diff % |
|------|--------|------------|---------|------|--------|
| 叶经理_1 | 0 | 476000 | 477023 | +1023 | 0.215% |
| 叶经理_1 | 1 | 352000 | 352175 | +175 | 0.050% |
| 叶经理_1 | 2 | 384000 | 384480 | +480 | 0.125% |
| 叶经理_1 | 3 | 294000 | 295727 | +1727 | 0.587% |
| 叶经理_1 | 4 | 512000 | 513743 | +1743 | 0.340% |
| 叶经理_1 | 5 | 214000 | 214560 | +560 | 0.262% |
| 叶经理_1 | 6 | 320000 | 320927 | +927 | 0.290% |
| 叶经理_1 | 7 | 352000 | 352175 | +175 | 0.050% |
| 叶经理_1 | 8 | 316000 | 317039 | +1039 | 0.329% |
| 叶经理_2 | 0 | 176000 | 177743 | +1743 | 0.990% |
| 叶经理_2 | 1 | 176000 | 177743 | +1743 | 0.990% |
| 叶经理_2 | 2 | 196000 | 197663 | +1663 | 0.848% |
| 叶经理_2 | 3 | 252000 | 253535 | +1535 | 0.609% |
| 叶经理_2 | 4 | 202000 | 202223 | +223 | 0.110% |
| 叶经理_2 | 5 | 330000 | 331535 | +1535 | 0.465% |
| 叶经理_2 | 6 | 270000 | 270240 | +240 | 0.089% |
| 叶经理_2 | 7 | 172000 | 173807 | +1807 | 1.051% |
| 叶经理_3 | 0 | 398000 | 398975 | +975 | 0.245% |
| 叶经理_3 | 1 | 204000 | 204480 | +480 | 0.235% |
| 叶经理_3 | 2 | 452000 | 452447 | +447 | 0.099% |
| 叶经理_3 | 3 | 244000 | 245760 | +1760 | 0.721% |
| 叶经理_3 | 4 | 274000 | 274127 | +127 | 0.046% |
| 叶经理_4 | 0 | 172000 | 173807 | +1807 | 1.051% |
| 叶经理_4 | 1 | 378000 | 379007 | +1007 | 0.266% |

---

## 7. MobID Prefix Analysis

| Mob Type | Correct Prefix | Ours Prefix | Match? |
|----------|---------------|-------------|--------|
| CompositionMob | 060a2b34.01010101.01010f00.13000000 | 060a2b34.01010101.01010f00.13000000 | ✅ |
| MasterMob | 060a2b34.01010105.01010d43.13000000 | 060a2b34.01010105.01010d43.13000000 | ✅ |
| SourceMob | 060a2b34.01010105.01010d43.13000000 | 060a2b34.01010105.01010d43.13000000 | ✅ |

---

## 8. Key Differences Summary

### Critical Differences (likely cause of Pro Tools import failure)

1. **CompositionMob Segment Structure**
   - **Correct**: Each audio clip wrapped in `OperationGroup` with `ConstantValue` parameter
   - **Ours**: Audio clips are bare `SourceClip` (no OperationGroup wrapper)
   - **Impact**: Pro Tools may expect OperationGroup structure for audio with effects metadata

2. **Clip Length Precision**
   - **Correct**: Clean integer sample counts (476000, 352000, 384000...)
   - **Ours**: Fractional conversion residuals (477023, 352175, 384480...)
   - **Impact**: Cumulative timing drift across clips, potential sync issues

3. **Mob Names**
   - **Correct**: Short names like `'A1-0001_01_叶经理_rate1'`
   - **Ours**: Full filenames like `'A1-0001_01_叶经理_rate1.0_260515_10PM_69e9_MiniMax_SJH'`
   - **Impact**: May affect track display in Pro Tools

### Minor Differences

4. **CompositionMob Name**: `'飞驰人生测试_20260515'` vs `'Timeline 1'`
5. **Header Version**: Both 1.1 ✅ (previously fixed)
6. **URL Encoding**: Both use `file:///` with percent-encoded Chinese ✅
