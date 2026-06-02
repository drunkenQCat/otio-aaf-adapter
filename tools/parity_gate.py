#!/usr/bin/env python
"""
parity_gate.py — AAF 输出一致性验证工具

对 correct_timeline.aaf (DaVinci Resolve) 和 test_output.aaf (otio-aaf-adapter)
进行语义级对比和二进制差异统计。PASS/FAIL 完全由语义检查决定。
"""

import aaf2
import argparse
import datetime
import os
import struct
import sys
from collections import defaultdict

CORRECT_AAF_PATH = "correct_timeline.aaf"
TEST_AAF_PATH = "test_output.aaf"
TRACKER_PATH = "parity_tracker.md"
TRACKER_ANCHOR = "<!-- convergence-log-end -->"


class CheckResult:
    __slots__ = ('status', 'layer', 'path', 'expected', 'actual', 'reason', 'tracker_id')

    def __init__(self, status, layer, path, expected=None, actual=None,
                 reason="", tracker_id=None):
        self.status = status
        self.layer = layer
        self.path = path
        self.expected = expected
        self.actual = actual
        self.reason = reason
        self.tracker_id = tracker_id


def safe_val(obj, key, default=None):
    try:
        v = obj[key].value
        if isinstance(v, list):
            return list(v)
        return v
    except (KeyError, AttributeError):
        try:
            return getattr(obj, key, default)
        except Exception:
            return default


def mob_key(mob):
    desc_type = ""
    if hasattr(mob, 'descriptor') and mob.descriptor:
        desc_type = mob.descriptor.__class__.__name__
    return (mob.__class__.__name__, desc_type)


def align_mobs(correct_mobs, test_mobs):
    groups_c = defaultdict(list)
    groups_t = defaultdict(list)
    for m in correct_mobs:
        groups_c[mob_key(m)].append(m)
    for m in test_mobs:
        groups_t[mob_key(m)].append(m)
    aligned = []
    for key in sorted(set(groups_c.keys()) | set(groups_t.keys())):
        cl = groups_c[key]
        tl = groups_t[key]
        for i in range(max(len(cl), len(tl))):
            aligned.append((cl[i] if i < len(cl) else None,
                            tl[i] if i < len(tl) else None))
    return aligned


def mob_id_prefix(mob_id_str):
    uid = str(mob_id_str).replace('urn:smpte:umid:', '')
    return '.'.join(uid.split('.')[:4])


def parse_wav_summary(summary_bytes):
    b = bytes(summary_bytes) if not isinstance(summary_bytes, (bytes, bytearray)) else summary_bytes
    if len(b) < 44:
        return {}
    return {
        'riff_size': struct.unpack_from('<I', b, 4)[0],
        'sample_rate': struct.unpack_from('<I', b, 24)[0],
        'byte_rate': struct.unpack_from('<I', b, 28)[0],
        'block_align': struct.unpack_from('<H', b, 32)[0],
        'bits_per_sample': struct.unpack_from('<H', b, 34)[0],
        'data_size': struct.unpack_from('<I', b, 40)[0],
    }


def url_filename(url_str):
    if not url_str:
        return ""
    s = str(url_str)
    for sep in ('/', '\\'):
        if sep in s:
            s = s.rsplit(sep, 1)[-1]
    return s


class ParityGate:
    def __init__(self, correct_path, test_path):
        self.correct_path = correct_path
        self.test_path = test_path

    def run(self, semantic_only=False, binary_only=False):
        semantic_results = []
        binary_stats = {}
        l0_results = []

        if not binary_only:
            semantic_results = self.run_semantic_checks()
            l0_results = self.run_l0_checks()

        if not semantic_only:
            binary_stats = self.run_binary_diff()

        return semantic_results, binary_stats, l0_results

    def run_semantic_checks(self):
        results = []
        with aaf2.open(self.correct_path) as fc, aaf2.open(self.test_path) as ft:
            results.extend(self._check_L1(fc, ft))
            results.extend(self._check_L2(fc, ft))
            results.extend(self._check_L3(fc, ft))
        return results

    # ── L1: Header ──────────────────────────────────────────────

    def _check_L1(self, fc, ft):
        r = []
        hc, ht = fc.header, ft.header

        # L1.01 — Header.Version  (#1)
        vc, vt = hc['Version'].value, ht['Version'].value
        r.append(CheckResult(
            "PASS" if vc == vt else "FAIL", "L1", "Header.Version",
            vc, vt, tracker_id=1))

        # L1.02 — OperationalPattern
        opc = safe_val(hc, 'OperationalPattern')
        opt = safe_val(ht, 'OperationalPattern')
        r.append(CheckResult(
            "PASS" if opc == opt else "FAIL", "L1", "Header.OperationalPattern",
            opc, opt))

        # L1.03 — ObjectModelVersion (whitelisted)
        omc = hc['ObjectModelVersion'].value
        omt = ht['ObjectModelVersion'].value
        r.append(CheckResult(
            "SKIP", "L1", "Header.ObjectModelVersion",
            omc, omt, reason="whitelisted: pyaaf2 internal"))

        # L1.04 — IdentificationList count
        ic = list(hc['IdentificationList'].value)
        it = list(ht['IdentificationList'].value)
        r.append(CheckResult(
            "PASS" if len(ic) == len(it) else "FAIL", "L1",
            "IdentificationList.count", len(ic), len(it)))

        if not ic or not it:
            return r

        idc, idt = ic[0], it[0]

        # L1.05 — CompanyName
        nc, nt = safe_val(idc, 'CompanyName', ''), safe_val(idt, 'CompanyName', '')
        r.append(CheckResult(
            "PASS" if nc == nt else "FAIL", "L1",
            "Identification[0].CompanyName", nc, nt))

        # L1.06 — ProductName
        nc, nt = safe_val(idc, 'ProductName', ''), safe_val(idt, 'ProductName', '')
        r.append(CheckResult(
            "PASS" if nc == nt else "FAIL", "L1",
            "Identification[0].ProductName", nc, nt))

        # L1.07 — ProductVersionString  (#3)
        vc, vt = safe_val(idc, 'ProductVersionString', ''), safe_val(idt, 'ProductVersionString', '')
        r.append(CheckResult(
            "PASS" if vc == vt else "FAIL", "L1",
            "Identification[0].ProductVersionString", vc, vt,
            tracker_id=3))

        # L1.08 — ProductVersion  (#4)
        pvc = safe_val(idc, 'ProductVersion')
        pvt = safe_val(idt, 'ProductVersion')
        r.append(CheckResult(
            "PASS" if pvc == pvt else "FAIL", "L1",
            "Identification[0].ProductVersion", pvc, pvt,
            tracker_id=4))

        # L1.09 — ToolkitVersion  (#5)
        tvc = safe_val(idc, 'ToolkitVersion')
        tvt = safe_val(idt, 'ToolkitVersion')
        r.append(CheckResult(
            "PASS" if tvc == tvt else "FAIL", "L1",
            "Identification[0].ToolkitVersion", tvc, tvt,
            tracker_id=5))

        # L1.10 — Platform
        pc, pt_ = safe_val(idc, 'Platform', ''), safe_val(idt, 'Platform', '')
        r.append(CheckResult(
            "PASS" if pc == pt_ else "FAIL", "L1",
            "Identification[0].Platform", pc, pt_))

        # L1.11 — ProductID
        pic = safe_val(idc, 'ProductID')
        pit = safe_val(idt, 'ProductID')
        r.append(CheckResult(
            "PASS" if str(pic) == str(pit) else "FAIL", "L1",
            "Identification[0].ProductID", str(pic), str(pit)))

        # L1.12 — Date (whitelisted, #6)
        r.append(CheckResult(
            "SKIP", "L1", "Identification[0].Date",
            reason="whitelisted: timestamp", tracker_id=6))

        # L1.13 — GenerationAUID (whitelisted, #7)
        r.append(CheckResult(
            "SKIP", "L1", "Identification[0].GenerationAUID",
            reason="whitelisted: uuid", tracker_id=7))

        return r

    # ── L2: Mob Structure ───────────────────────────────────────

    def _check_L2(self, fc, ft):
        r = []
        mobs_c = list(fc.content.mobs)
        mobs_t = list(ft.content.mobs)

        # L2.01 — Mob count
        r.append(CheckResult(
            "PASS" if len(mobs_c) == len(mobs_t) else "FAIL", "L2",
            "ContentStorage.Mobs.count", len(mobs_c), len(mobs_t)))

        # L2.02 — Mob type sequence
        seq_c = [m.__class__.__name__ for m in mobs_c]
        seq_t = [m.__class__.__name__ for m in mobs_t]
        r.append(CheckResult(
            "PASS" if seq_c == seq_t else "FAIL", "L2",
            "Mob.type_sequence", seq_c, seq_t))

        aligned = align_mobs(mobs_c, mobs_t)

        # L2.03 — Mob names (per aligned pair)
        for i, (mc, mt_) in enumerate(aligned):
            if mc is None or mt_ is None:
                r.append(CheckResult("FAIL", "L2",
                    f"Mob[{i}].existence",
                    mc.__class__.__name__ if mc else "MISSING",
                    mt_.__class__.__name__ if mt_ else "MISSING"))
                continue
            key = mob_key(mc)
            label = f"{key[0]}"
            if key[1]:
                label += f"[{key[1]}]"
            nc, nt = mc.name, mt_.name
            r.append(CheckResult(
                "PASS" if nc == nt else "FAIL", "L2",
                f"{label}.name", nc, nt))

        # L2.04 / L2.05 — Slot counts
        for i, (mc, mt_) in enumerate(aligned):
            if mc is None or mt_ is None:
                continue
            key = mob_key(mc)
            label = f"{key[0]}"
            if key[1]:
                label += f"[{key[1]}]"
            sc = len(list(mc.slots))
            st = len(list(mt_.slots))
            is_comp = mc.__class__.__name__ == 'CompositionMob'
            tid = 8 if is_comp else None
            chk_id = "L2.04" if is_comp else "L2.05"
            r.append(CheckResult(
                "PASS" if sc == st else "FAIL", "L2",
                f"{label}.Slots.count", sc, st,
                tracker_id=tid))

        # L2.06 — MobID prefix
        for i, (mc, mt_) in enumerate(aligned):
            if mc is None or mt_ is None:
                continue
            key = mob_key(mc)
            label = f"{key[0]}"
            if key[1]:
                label += f"[{key[1]}]"
            pc = mob_id_prefix(mc.mob_id)
            pt = mob_id_prefix(mt_.mob_id)
            # Assign tracker_id for MobID prefix differences
            if mc.__class__.__name__ == 'MasterMob':
                tid = 28
            elif mc.__class__.__name__ == 'SourceMob':
                tid = 29 if key[1] == 'TapeDescriptor' else 30
            else:
                tid = None
            r.append(CheckResult(
                "PASS" if pc == pt else "FAIL", "L2",
                f"{label}.MobID.prefix", pc, pt,
                tracker_id=tid))

        # L2.07 — MobID UUID (whitelisted)
        r.append(CheckResult(
            "SKIP", "L2", "Mob[*].MobID.uuid_part",
            reason="whitelisted: uuid"))

        # Per-slot checks for each aligned mob pair
        for i, (mc, mt_) in enumerate(aligned):
            if mc is None or mt_ is None:
                continue
            key = mob_key(mc)
            mob_label = f"{key[0]}"
            if key[1]:
                mob_label += f"[{key[1]}]"
            is_comp = mc.__class__.__name__ == 'CompositionMob'
            is_master = mc.__class__.__name__ == 'MasterMob'
            is_source = mc.__class__.__name__ == 'SourceMob'

            slots_c = list(mc.slots)
            slots_t = list(mt_.slots)

            # Align slots: by SlotID for CompositionMob (slot counts may differ),
            # by index for other mobs
            if is_comp:
                slot_map_c = {s.slot_id: s for s in slots_c}
                slot_map_t = {s.slot_id: s for s in slots_t}
                all_slot_ids = sorted(set(slot_map_c.keys()) | set(slot_map_t.keys()))
                slot_pairs = []
                for sid in all_slot_ids:
                    slot_pairs.append((
                        slot_map_c.get(sid),
                        slot_map_t.get(sid),
                        sid
                    ))
            else:
                slot_pairs = []
                for j in range(max(len(slots_c), len(slots_t))):
                    slot_pairs.append((
                        slots_c[j] if j < len(slots_c) else None,
                        slots_t[j] if j < len(slots_t) else None,
                        j
                    ))

            for sc, st, slot_key in slot_pairs:
                if sc is None or st is None:
                    r.append(CheckResult("FAIL", "L2",
                        f"{mob_label}.Slot[{slot_key}].existence",
                        "present" if sc else "MISSING",
                        "present" if st else "MISSING",
                        tracker_id=8 if is_comp and sc is None else None))
                    continue

                seg_c = sc.segment
                seg_t = st.segment
                slot_label = f"{mob_label}.Slot[{slot_key}]"

                # L2.08 — slot_id
                tid = 10 if is_comp else None
                r.append(CheckResult(
                    "PASS" if sc.slot_id == st.slot_id else "FAIL", "L2",
                    f"{slot_label}.slot_id", sc.slot_id, st.slot_id,
                    tracker_id=tid))

                # L2.09 — edit_rate
                er_c = str(sc.edit_rate)
                er_t = str(st.edit_rate)
                tid = 11 if is_comp else None
                r.append(CheckResult(
                    "PASS" if er_c == er_t else "FAIL", "L2",
                    f"{slot_label}.edit_rate", er_c, er_t,
                    tracker_id=tid))

                # L2.09b / L2.10 / L2.11 / L2.12 — PhysicalTrackNumber
                ptc = safe_val(sc, 'PhysicalTrackNumber')
                ptt = safe_val(st, 'PhysicalTrackNumber')
                if is_comp:
                    tid = 12
                elif is_master:
                    tid = 15
                elif is_source:
                    tid = 16
                else:
                    tid = None
                r.append(CheckResult(
                    "PASS" if ptc == ptt else "FAIL", "L2",
                    f"{slot_label}.PhysicalTrackNumber", ptc, ptt,
                    tracker_id=tid))

                # L2.13 — Slot name
                nc = sc.name if hasattr(sc, 'name') else ''
                nt = st.name if hasattr(st, 'name') else ''
                # #11: CompositionMob TC slot name "" vs "TC"
                tid = 11 if is_comp and nc != nt else None
                r.append(CheckResult(
                    "PASS" if nc == nt else "FAIL", "L2",
                    f"{slot_label}.name", nc, nt,
                    tracker_id=tid))

                # L2.14 — Segment type
                seg_type_c = seg_c.__class__.__name__
                seg_type_t = seg_t.__class__.__name__
                r.append(CheckResult(
                    "PASS" if seg_type_c == seg_type_t else "FAIL", "L2",
                    f"{slot_label}.Segment.type", seg_type_c, seg_type_t))

                # Timecode-specific checks
                if seg_type_c == 'Timecode':
                    # L2.15 — start
                    sc_start = getattr(seg_c, 'start', None)
                    st_start = getattr(seg_t, 'start', None)
                    r.append(CheckResult(
                        "PASS" if sc_start == st_start else "FAIL", "L2",
                        f"{slot_label}.Timecode.start", sc_start, st_start))

                    # L2.16 — length (only track for CompositionMob = #9)
                    sc_len = getattr(seg_c, 'length', None)
                    st_len = getattr(seg_t, 'length', None)
                    tid = 9 if is_comp else None
                    r.append(CheckResult(
                        "PASS" if sc_len == st_len else "FAIL", "L2",
                        f"{slot_label}.Timecode.length", sc_len, st_len,
                        tracker_id=tid))

                    # L2.17 — fps
                    sc_fps = getattr(seg_c, 'fps', None)
                    st_fps = getattr(seg_t, 'fps', None)
                    r.append(CheckResult(
                        "PASS" if sc_fps == st_fps else "FAIL", "L2",
                        f"{slot_label}.Timecode.fps", sc_fps, st_fps))

                    # L2.18 — drop
                    sc_drop = getattr(seg_c, 'drop', None)
                    st_drop = getattr(seg_t, 'drop', None)
                    r.append(CheckResult(
                        "PASS" if sc_drop == st_drop else "FAIL", "L2",
                        f"{slot_label}.Timecode.drop", sc_drop, st_drop))

                # Sequence / SourceClip component checks
                if hasattr(seg_c, 'components') and hasattr(seg_t, 'components'):
                    comps_c = list(seg_c.components)
                    comps_t = list(seg_t.components)

                    # L2.19 — Component count
                    r.append(CheckResult(
                        "PASS" if len(comps_c) == len(comps_t) else "FAIL", "L2",
                        f"{slot_label}.Segment.Components.count",
                        len(comps_c), len(comps_t)))

                    for k in range(max(len(comps_c), len(comps_t))):
                        comp_label = f"{slot_label}.Component[{k}]"
                        if k >= len(comps_c) or k >= len(comps_t):
                            r.append(CheckResult("FAIL", "L2",
                                f"{comp_label}.existence",
                                "present" if k < len(comps_c) else "MISSING",
                                "present" if k < len(comps_t) else "MISSING"))
                            continue

                        cc = comps_c[k]
                        ct = comps_t[k]

                        # L2.20 — Component type
                        r.append(CheckResult(
                            "PASS" if cc.__class__.__name__ == ct.__class__.__name__ else "FAIL",
                            "L2", f"{comp_label}.type",
                            cc.__class__.__name__, ct.__class__.__name__))

                        # L2.21 — Component length
                        lc = getattr(cc, 'length', None)
                        lt = getattr(ct, 'length', None)
                        r.append(CheckResult(
                            "PASS" if lc == lt else "FAIL", "L2",
                            f"{comp_label}.length", lc, lt))

                        # L2.22 — SourceClip details
                        if cc.__class__.__name__ == 'SourceClip':
                            # source_mob_slot_id
                            src_c = safe_val(cc, 'SourceMobSlotID')
                            src_t = safe_val(ct, 'SourceMobSlotID')
                            if src_c is not None or src_t is not None:
                                r.append(CheckResult(
                                    "PASS" if src_c == src_t else "FAIL", "L2",
                                    f"{comp_label}.source_mob_slot_id",
                                    src_c, src_t))

                # Standalone SourceClip (not inside Sequence)
                elif seg_type_c == 'SourceClip':
                    # length
                    lc = getattr(seg_c, 'length', None)
                    lt = getattr(seg_t, 'length', None)
                    r.append(CheckResult(
                        "PASS" if lc == lt else "FAIL", "L2",
                        f"{slot_label}.SourceClip.length", lc, lt))
                    # source_mob_slot_id
                    src_c = safe_val(seg_c, 'SourceMobSlotID')
                    src_t = safe_val(seg_t, 'SourceMobSlotID')
                    if src_c is not None or src_t is not None:
                        r.append(CheckResult(
                            "PASS" if src_c == src_t else "FAIL", "L2",
                            f"{slot_label}.SourceClip.source_mob_slot_id",
                            src_c, src_t))

        return r

    # ── L3: Descriptor ─────────────────────────────────────────

    def _check_L3(self, fc, ft):
        r = []
        mobs_c = list(fc.content.mobs)
        mobs_t = list(ft.content.mobs)
        aligned = align_mobs(mobs_c, mobs_t)

        for i, (mc, mt_) in enumerate(aligned):
            if mc is None or mt_ is None:
                continue

            desc_c = mc.descriptor if hasattr(mc, 'descriptor') else None
            desc_t = mt_.descriptor if hasattr(mt_, 'descriptor') else None

            if desc_c is None and desc_t is None:
                continue

            key = mob_key(mc)
            mob_label = f"{key[0]}"
            if key[1]:
                mob_label += f"[{key[1]}]"

            # L3.01 — Descriptor type
            dt_c = desc_c.__class__.__name__ if desc_c else None
            dt_t = desc_t.__class__.__name__ if desc_t else None
            r.append(CheckResult(
                "PASS" if dt_c == dt_t else "FAIL", "L3",
                f"{mob_label}.Descriptor.type", dt_c, dt_t))

            if dt_c == 'TapeDescriptor':
                # L3.02 — TapeDescriptor existence
                r.append(CheckResult(
                    "PASS" if dt_t == 'TapeDescriptor' else "FAIL", "L3",
                    f"{mob_label}.TapeDescriptor.exists", True,
                    dt_t == 'TapeDescriptor'))
                continue

            if dt_c != 'WAVEDescriptor':
                continue

            # WAVEDescriptor checks
            # L3.03 — SampleRate
            sr_c = safe_val(desc_c, 'SampleRate')
            sr_t = safe_val(desc_t, 'SampleRate')
            r.append(CheckResult(
                "PASS" if sr_c == sr_t else "FAIL", "L3",
                "WAVEDescriptor.SampleRate", sr_c, sr_t))

            # L3.04 — AudioSamplingRate (if exists)
            asr_c = safe_val(desc_c, 'AudioSamplingRate')
            asr_t = safe_val(desc_t, 'AudioSamplingRate')
            if asr_c is not None or asr_t is not None:
                r.append(CheckResult(
                    "PASS" if asr_c == asr_t else "FAIL", "L3",
                    "WAVEDescriptor.AudioSamplingRate", asr_c, asr_t))

            # L3.05 — Length
            len_c = safe_val(desc_c, 'Length')
            len_t = safe_val(desc_t, 'Length')
            r.append(CheckResult(
                "PASS" if len_c == len_t else "FAIL", "L3",
                "WAVEDescriptor.Length", len_c, len_t))

            # Summary (WAV header)
            sum_c = safe_val(desc_c, 'Summary')
            sum_t = safe_val(desc_t, 'Summary')
            if sum_c is not None and sum_t is not None:
                b_c = bytes(sum_c) if not isinstance(sum_c, (bytes, bytearray)) else sum_c
                b_t = bytes(sum_t) if not isinstance(sum_t, (bytes, bytearray)) else sum_t

                # L3.11 (moved up) — Summary byte length
                r.append(CheckResult(
                    "PASS" if len(b_c) == len(b_t) else "FAIL", "L3",
                    "EssenceSummary.byte_length", len(b_c), len(b_t)))

                wav_c = parse_wav_summary(b_c)
                wav_t = parse_wav_summary(b_t)

                # L3.06 — wav_byte_rate  (#19)
                r.append(CheckResult(
                    "PASS" if wav_c['byte_rate'] == wav_t['byte_rate'] else "FAIL", "L3",
                    "Summary.wav_byte_rate", wav_c['byte_rate'], wav_t['byte_rate'],
                    tracker_id=19))

                # L3.07 — wav_block_align  (#20)
                r.append(CheckResult(
                    "PASS" if wav_c['block_align'] == wav_t['block_align'] else "FAIL", "L3",
                    "Summary.wav_block_align", wav_c['block_align'], wav_t['block_align'],
                    tracker_id=20))

                # L3.08 — wav_bits_per_sample  (#21)
                r.append(CheckResult(
                    "PASS" if wav_c['bits_per_sample'] == wav_t['bits_per_sample'] else "FAIL", "L3",
                    "Summary.wav_bits_per_sample", wav_c['bits_per_sample'], wav_t['bits_per_sample'],
                    tracker_id=21))

                # L3.09 — RIFF chunk size  (#22)
                riff_c = wav_c['riff_size']
                riff_t = wav_t['riff_size']
                # Check: correct should be non-zero, test should match
                r.append(CheckResult(
                    "PASS" if riff_c == riff_t else "FAIL", "L3",
                    "Summary.RIFF_chunk_size", riff_c, riff_t,
                    tracker_id=22))

                # L3.10 — data chunk size  (#23)
                data_c = wav_c['data_size']
                data_t = wav_t['data_size']
                r.append(CheckResult(
                    "PASS" if data_c == data_t else "FAIL", "L3",
                    "Summary.data_chunk_size", data_c, data_t,
                    tracker_id=23))

            # Locator checks
            locs_c = []
            locs_t = []
            try:
                locs_c = list(desc_c['Locator'].value)
            except Exception:
                pass
            try:
                locs_t = list(desc_t['Locator'].value)
            except Exception:
                pass

            # L3.11 — Locator count
            r.append(CheckResult(
                "PASS" if len(locs_c) == len(locs_t) else "FAIL", "L3",
                "Locator.count", len(locs_c), len(locs_t)))

            # L3.12 — NetworkLocator URL filename  (#24)
            if locs_c and locs_t:
                url_c = safe_val(locs_c[0], 'URLString', '')
                url_t = safe_val(locs_t[0], 'URLString', '')
                fn_c = url_filename(url_c)
                fn_t = url_filename(url_t)
                r.append(CheckResult(
                    "PASS" if fn_c == fn_t else "FAIL", "L3",
                    "NetworkLocator.URLString.filename", fn_c, fn_t,
                    tracker_id=24))

        return r

    # ── L0: Dictionary ─────────────────────────────────────────

    def run_l0_checks(self):
        r = []
        def_names = [
            ('ContainerDefinitions', 25),
            ('DataDefinitions', 26),
            ('CodecDefinitions', 27),
        ]

        with aaf2.open(self.correct_path) as fc, aaf2.open(self.test_path) as ft:
            for prop_name, tid in def_names:
                try:
                    items_c = set(str(x) for x in fc.dictionary[prop_name].value)
                except Exception:
                    items_c = set()
                try:
                    items_t = set(str(x) for x in ft.dictionary[prop_name].value)
                except Exception:
                    items_t = set()

                only_c = items_c - items_t
                only_t = items_t - items_c

                status = "PASS" if not only_c and not only_t else "FAIL"
                detail = ""
                if only_c or only_t:
                    parts = []
                    if only_c:
                        parts.append(f"only_in_correct={len(only_c)}")
                    if only_t:
                        parts.append(f"only_in_test={len(only_t)}")
                    detail = ", ".join(parts)

                r.append(CheckResult(
                    status, "L0", f"Dictionary.{prop_name}",
                    f"Correct={len(items_c)}", f"Test={len(items_t)}",
                    reason=detail, tracker_id=tid))

        return r

    # ── Binary diff ────────────────────────────────────────────

    def run_binary_diff(self):
        with open(self.correct_path, 'rb') as fc, open(self.test_path, 'rb') as ft:
            data_c = fc.read()
            data_t = ft.read()

        size_c = len(data_c)
        size_t = len(data_t)
        min_len = min(size_c, size_t)

        diff_bytes = 0
        diff_groups = 0
        in_diff = False

        for i in range(min_len):
            if data_c[i] != data_t[i]:
                diff_bytes += 1
                if not in_diff:
                    diff_groups += 1
                    in_diff = True
            else:
                in_diff = False

        diff_bytes += abs(size_c - size_t)

        return {
            'size_correct': size_c,
            'size_test': size_t,
            'diff_bytes': diff_bytes,
            'diff_groups': diff_groups,
        }

    # ── Update tracker ─────────────────────────────────────────

    def update_tracker(self, semantic_results, binary_stats, note=""):
        today = datetime.date.today().isoformat()
        fail_count = sum(1 for r in semantic_results if r.status == "FAIL")
        bg = binary_stats.get('diff_groups', '—')
        bb = binary_stats.get('diff_bytes', '—')
        line = f"| {today} | {fail_count} | {bg} | {bb} | {note} |"

        if not os.path.exists(TRACKER_PATH):
            print(f"WARNING: {TRACKER_PATH} not found, skipping update")
            return

        with open(TRACKER_PATH, encoding='utf-8') as f:
            content = f.read()

        if TRACKER_ANCHOR not in content:
            print(f"WARNING: anchor '{TRACKER_ANCHOR}' not found, skipping update")
            return

        content = content.replace(TRACKER_ANCHOR, f"{line}\n{TRACKER_ANCHOR}")
        with open(TRACKER_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Tracker updated: {line}")


# ── Output formatting ──────────────────────────────────────────

def format_summary(results, binary_stats, l0_results):
    lines = []
    lines.append("AAF Parity Gate")
    lines.append("═" * 40)
    lines.append("")

    for layer, label in [("L1", "Header"), ("L2", "Mob Structure"), ("L3", "Descriptor")]:
        items = [r for r in results if r.layer == layer]
        total = len(items)
        passes = sum(1 for r in items if r.status == "PASS")
        fails = sum(1 for r in items if r.status == "FAIL")
        skips = sum(1 for r in items if r.status == "SKIP")
        parts = []
        if passes:
            parts.append(f"{passes} PASS")
        if fails:
            parts.append(f"{fails} FAIL")
        if skips:
            parts.append(f"{skips} SKIP")
        lines.append(f"[{layer} - {label}]".ljust(25) + f"{total} checks: {', '.join(parts)}")

    if binary_stats:
        lines.append(f"[Binary]".ljust(25) +
            f"{binary_stats.get('diff_groups', 0)} diff groups, "
            f"{binary_stats.get('diff_bytes', 0)} diff bytes (info only)")

    if l0_results:
        for r in l0_results:
            lines.append(f"[L0 - INFO]  {r.path}: {r.expected} vs {r.actual} ({r.reason})")

    lines.append("")

    fail_items = [r for r in results if r.status == "FAIL"]
    if fail_items:
        lines.append(f"RESULT: FAIL ({len(fail_items)} errors)")
        for r in fail_items:
            tid = f"#{r.tracker_id}" if r.tracker_id else "#-"
            lines.append(f"  {tid:>5}  {r.path}: expected {r.expected}, got {r.actual}")
    else:
        lines.append("RESULT: PASS")

    return '\n'.join(lines)


def format_verbose(results, binary_stats, l0_results):
    lines = []
    lines.append("AAF Parity Gate (verbose)")
    lines.append("═" * 40)
    lines.append("")

    for layer, label in [("L1", "Header"), ("L2", "Mob Structure"), ("L3", "Descriptor")]:
        items = [r for r in results if r.layer == layer]
        lines.append(f"[{layer} - {label}]")
        for r in items:
            tid = f"#{r.tracker_id}" if r.tracker_id else "#-"
            if r.status == "SKIP":
                lines.append(f"  SKIP  [{tid:>4}]  {r.path}: ({r.reason})")
            elif r.status == "PASS":
                val_str = f"{r.expected!r} == {r.actual!r}"
                lines.append(f"  PASS  [{tid:>4}]  {r.path}: {val_str}")
            else:
                lines.append(f"  FAIL  [{tid:>4}]  {r.path}: expected {r.expected!r}, got {r.actual!r}")
        lines.append("")

    if binary_stats:
        lines.append("[Binary] (info only — does not affect PASS/FAIL)")
        lines.append(f"  File sizes: correct={binary_stats['size_correct']}, test={binary_stats['size_test']}")
        lines.append(f"  Total diff bytes: {binary_stats['diff_bytes']}")
        lines.append(f"  Total diff groups: {binary_stats['diff_groups']}")
        lines.append("")

    if l0_results:
        lines.append("[L0 - Dictionary] (info only)")
        for r in l0_results:
            lines.append(f"  {r.path}: {r.expected} vs {r.actual} ({r.reason})")
        lines.append("")

    fail_items = [r for r in results if r.status == "FAIL"]
    lines.append("─" * 40)
    if fail_items:
        lines.append(f"RESULT: FAIL ({len(fail_items)} semantic errors)")
    else:
        lines.append("RESULT: PASS")
    lines.append("─" * 40)

    return '\n'.join(lines)


# ── Main ───────────────────────────────────────────────────────

def do_export():
    """Run test_export.py logic inline."""
    import opentimelineio as otio
    timeline = otio.adapters.read_from_file("SimpleTimeline.otio")
    otio.adapters.write_to_file(timeline, TEST_AAF_PATH)


def main():
    parser = argparse.ArgumentParser(description="AAF Parity Gate")
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--semantic-only', action='store_true')
    parser.add_argument('--binary-only', action='store_true')
    parser.add_argument('--skip-export', action='store_true')
    parser.add_argument('--update-tracker', action='store_true')
    parser.add_argument('--correct', default=CORRECT_AAF_PATH)
    parser.add_argument('--test', default=TEST_AAF_PATH)
    args = parser.parse_args()

    try:
        if not args.skip_export and not args.binary_only:
            do_export()

        gate = ParityGate(args.correct, args.test)
        results, binary_stats, l0_results = gate.run(
            semantic_only=args.semantic_only,
            binary_only=args.binary_only)

        if args.verbose:
            print(format_verbose(results, binary_stats, l0_results))
        else:
            print(format_summary(results, binary_stats, l0_results))

        if args.update_tracker:
            gate.update_tracker(results, binary_stats)

        fail_count = sum(1 for r in results if r.status == "FAIL")
        sys.exit(1 if fail_count > 0 else 0)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
