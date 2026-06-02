#!/usr/bin/env python
"""深入对比两个 AAF 文件的所有关键属性"""

import aaf2
from collections import OrderedDict


def safe_get(obj, key, default=None):
    """安全获取 pyaaf2 对象的属性值"""
    try:
        return obj[key].value
    except Exception:
        try:
            return getattr(obj, key, default)
        except Exception:
            return default


def get_mob_info(mob):
    """获取 Mob 的详细信息"""
    info = OrderedDict()
    info['class'] = mob.__class__.__name__
    info['name'] = mob.name
    info['mob_id'] = str(mob.mob_id)
    info['slots'] = []

    for slot in mob.slots:
        slot_info = OrderedDict()
        slot_info['slot_id'] = slot.slot_id
        slot_info['slot_name'] = slot.name if hasattr(slot, 'name') else 'N/A'
        slot_info['edit_rate'] = str(slot.edit_rate)
        slot_info['physical_track_number'] = safe_get(slot, 'PhysicalTrackNumber')

        # Segment info
        segment = slot.segment
        seg_info = OrderedDict()
        seg_info['type'] = segment.__class__.__name__

        if hasattr(segment, 'length'):
            seg_info['length'] = segment.length
        if hasattr(segment, 'start'):
            seg_info['start'] = segment.start
        if hasattr(segment, 'fps'):
            seg_info['fps'] = segment.fps
        if hasattr(segment, 'drop'):
            seg_info['drop'] = segment.drop

        # Components for Sequence
        if hasattr(segment, 'components'):
            seg_info['components'] = []
            for comp in segment.components:
                comp_info = OrderedDict()
                comp_info['type'] = comp.__class__.__name__
                if hasattr(comp, 'length'):
                    comp_info['length'] = comp.length
                if hasattr(comp, 'source_id'):
                    comp_info['source_id'] = str(comp.source_id) if comp.source_id else None
                if hasattr(comp, 'source_mob_slot_id'):
                    comp_info['source_mob_slot_id'] = comp.source_mob_slot_id
                if hasattr(comp, 'start_time'):
                    comp_info['start_time'] = comp.start_time
                seg_info['components'].append(comp_info)

        # OperationGroup info
        if hasattr(segment, 'operation'):
            seg_info['operation'] = str(segment.operation) if segment.operation else None
        if hasattr(segment, 'parameters'):
            seg_info['parameters_count'] = len(list(segment.parameters))

        slot_info['segment'] = seg_info
        info['slots'].append(slot_info)

    # EssenceDescription
    if hasattr(mob, 'descriptor') and mob.descriptor:
        desc_info = OrderedDict()
        desc_info['type'] = mob.descriptor.__class__.__name__
        desc = mob.descriptor
        desc_info['sample_rate'] = str(safe_get(desc, 'SampleRate', 'N/A'))
        desc_info['length'] = safe_get(desc, 'Length', 'N/A')
        desc_info['channels'] = safe_get(desc, 'Channels', 'N/A')
        desc_info['audio_sampling_rate'] = str(safe_get(desc, 'AudioSamplingRate', 'N/A'))
        desc_info['quantization_bits'] = safe_get(desc, 'QuantizationBits', 'N/A')
        summary_val = safe_get(desc, 'Summary')
        desc_info['has_summary'] = summary_val is not None
        if isinstance(summary_val, (bytes, bytearray)):
            desc_info['summary_length'] = len(summary_val)
        # Locator
        try:
            locators = list(desc['Locator'].value)
            desc_info['locator_count'] = len(locators)
            if locators:
                desc_info['locators'] = []
                for loc in locators:
                    url = safe_get(loc, 'URLString', 'N/A')
                    desc_info['locators'].append(str(url))
        except Exception:
            desc_info['locator_count'] = 0
        info['descriptor'] = desc_info

    return info


def compare_aaf_files(file1_path, file2_path):
    """对比两个 AAF 文件"""
    print("=" * 100)
    print("AAF 文件深入对比报告")
    print("=" * 100)

    with aaf2.open(file1_path) as f1, aaf2.open(file2_path) as f2:
        print(f"\n文件 1 (Correct): {file1_path}")
        print(f"文件 2 (Test):    {file2_path}")

        # 比较 Header
        print("\n" + "=" * 100)
        print("### Header 对比 ###")
        print("=" * 100)

        for prop_name in ['Version', 'ObjectModelVersion']:
            val1 = safe_get(f1.header, prop_name, None)
            val2 = safe_get(f2.header, prop_name, None)
            match = "OK" if str(val1) == str(val2) else "DIFF"
            print(f"  {prop_name}: {match}")
            print(f"    Correct: {val1}")
            print(f"    Test:    {val2}")

        # OperationalPattern
        op1 = safe_get(f1.header, 'OperationalPattern', 'NOT SET')
        op2 = safe_get(f2.header, 'OperationalPattern', 'NOT SET')
        match = "OK" if str(op1) == str(op2) else "DIFF"
        print(f"  OperationalPattern: {match}")
        print(f"    Correct: {op1}")
        print(f"    Test:    {op2}")

        # EssenceContainers
        try:
            ec1 = list(f1.header['EssenceContainers'].value)
            ec1_str = [str(safe_get(ec, 'EssenceContainer', 'N/A')) for ec in ec1]
        except Exception:
            ec1_str = ['N/A']
        try:
            ec2 = list(f2.header['EssenceContainers'].value)
            ec2_str = [str(safe_get(ec, 'EssenceContainer', 'N/A')) for ec in ec2]
        except Exception:
            ec2_str = ['N/A']
        match = "OK" if ec1_str == ec2_str else "DIFF"
        print(f"  EssenceContainers: {match}")
        print(f"    Correct: {ec1_str}")
        print(f"    Test:    {ec2_str}")

        # 比较 Identification
        print("\n### Identification 对比 ###")
        try:
            idents1 = list(f1.header['IdentificationList'].value)
        except Exception:
            idents1 = []
        try:
            idents2 = list(f2.header['IdentificationList'].value)
        except Exception:
            idents2 = []

        print(f"  数量: Correct={len(idents1)}, Test={len(idents2)}")

        for idx, (id1, id2) in enumerate(zip(idents1, idents2)):
            print(f"\n  --- Identification [{idx}] ---")
            for prop_name in ['CompanyName', 'ProductName', 'ProductVersionString',
                              'Platform', 'ProductID', 'Date', 'GenerationAUID']:
                val1 = safe_get(id1, prop_name, 'N/A')
                val2 = safe_get(id2, prop_name, 'N/A')
                if prop_name in ('Date', 'GenerationAUID'):
                    match = "⊘ (不可控)"
                else:
                    match = "✓" if str(val1) == str(val2) else "⚠️"
                print(f"    {prop_name}: {match}")
                print(f"      Correct: {val1}")
                print(f"      Test:    {val2}")

        # 比较 Mobs
        print("\n" + "=" * 100)
        print("### Mobs 对比 ###")
        print("=" * 100)

        mobs1 = list(f1.content.mobs)
        mobs2 = list(f2.content.mobs)

        print(f"\nMob 数量：Correct={len(mobs1)}, Test={len(mobs2)}")
        print(f"Mob 类型序列 (Correct): {[m.__class__.__name__ for m in mobs1]}")
        print(f"Mob 类型序列 (Test):    {[m.__class__.__name__ for m in mobs2]}")

        # 按类型分组
        def group_mobs_by_type(mobs):
            groups = {'CompositionMob': [], 'MasterMob': [], 'SourceMob': []}
            for mob in mobs:
                mob_type = mob.__class__.__name__
                if mob_type in groups:
                    groups[mob_type].append(mob)
            return groups

        groups1 = group_mobs_by_type(mobs1)
        groups2 = group_mobs_by_type(mobs2)

        for mob_type in ['CompositionMob', 'MasterMob', 'SourceMob']:
            print(f"\n{'=' * 80}")
            print(f"### {mob_type} 对比 ###")
            print(f"{'=' * 80}")

            type_mobs1 = groups1.get(mob_type, [])
            type_mobs2 = groups2.get(mob_type, [])

            print(f"数量：Correct={len(type_mobs1)}, Test={len(type_mobs2)}")

            max_count = max(len(type_mobs1), len(type_mobs2))
            for i in range(max_count):
                if i >= len(type_mobs1):
                    print(f"\n  [{mob_type} #{i+1}] 仅在 Test 中存在")
                    info2 = get_mob_info(type_mobs2[i])
                    print(f"    name: '{info2['name']}' slots: {len(info2['slots'])}")
                    continue
                if i >= len(type_mobs2):
                    print(f"\n  [{mob_type} #{i+1}] 仅在 Correct 中存在")
                    info1 = get_mob_info(type_mobs1[i])
                    print(f"    name: '{info1['name']}' slots: {len(info1['slots'])}")
                    continue

                mob1 = type_mobs1[i]
                mob2 = type_mobs2[i]
                print(f"\n  [{mob_type} #{i+1}]")

                info1 = get_mob_info(mob1)
                info2 = get_mob_info(mob2)

                # 比较基本信息
                for key in ['name']:
                    val1 = info1.get(key, 'N/A')
                    val2 = info2.get(key, 'N/A')
                    match = "✓" if val1 == val2 else "⚠️"
                    print(f"    {key}: {match} '{val1}' vs '{val2}'")

                # 比较槽位
                slots1 = info1.get('slots', [])
                slots2 = info2.get('slots', [])
                print(f"    槽位数量：{'✓' if len(slots1) == len(slots2) else '❌'} {len(slots1)} vs {len(slots2)}")

                max_slots = max(len(slots1), len(slots2))
                for j in range(max_slots):
                    if j >= len(slots1):
                        s2 = slots2[j]
                        print(f"\n      Slot #{j+1}: 仅在 Test 中 (SlotID={s2.get('slot_id')}, EditRate={s2.get('edit_rate')})")
                        continue
                    if j >= len(slots2):
                        s1 = slots1[j]
                        print(f"\n      Slot #{j+1}: 仅在 Correct 中 (SlotID={s1.get('slot_id')}, EditRate={s1.get('edit_rate')})")
                        continue

                    slot1 = slots1[j]
                    slot2 = slots2[j]
                    print(f"\n      Slot #{j+1}:")

                    for key in ['slot_id', 'edit_rate']:
                        val1 = slot1.get(key, 'N/A')
                        val2 = slot2.get(key, 'N/A')
                        match = "✓" if str(val1) == str(val2) else "❌"
                        print(f"        {key}: {match} {val1} vs {val2}")

                    # 比较 Segment
                    seg1 = slot1.get('segment', {})
                    seg2 = slot2.get('segment', {})

                    print(f"\n        Segment:")
                    for key in ['type', 'length', 'start', 'fps']:
                        val1 = seg1.get(key, 'N/A')
                        val2 = seg2.get(key, 'N/A')
                        match = "✓" if str(val1) == str(val2) else "❌"
                        print(f"          {key}: {match} {val1} vs {val2}")

                    # 比较 Components
                    comps1 = seg1.get('components', [])
                    comps2 = seg2.get('components', [])
                    if comps1 or comps2:
                        print(f"\n        Components: {'✓' if len(comps1) == len(comps2) else '❌'} {len(comps1)} vs {len(comps2)}")
                        for k in range(max(len(comps1), len(comps2))):
                            if k >= len(comps1):
                                print(f"\n          Component #{k+1}: 仅在 Test ({comps2[k].get('type', '?')})")
                                continue
                            if k >= len(comps2):
                                print(f"\n          Component #{k+1}: 仅在 Correct ({comps1[k].get('type', '?')})")
                                continue
                            comp1 = comps1[k]
                            comp2 = comps2[k]
                            print(f"\n          Component #{k+1} ({comp1.get('type', '?')}):")
                            for key in ['type', 'length', 'source_mob_slot_id', 'start_time']:
                                val1 = comp1.get(key, 'N/A')
                                val2 = comp2.get(key, 'N/A')
                                match = "✓" if str(val1) == str(val2) else "❌"
                                print(f"            {key}: {match} {val1} vs {val2}")

                    # 比较 PhysicalTrackNumber
                    pt1 = slot1.get('physical_track_number', None)
                    pt2 = slot2.get('physical_track_number', None)
                    if pt1 is not None or pt2 is not None:
                        match = "✓" if pt1 == pt2 else "⚠️"
                        print(f"\n        PhysicalTrackNumber: {match} {pt1} vs {pt2}")

                # 比较 Descriptor
                desc1 = info1.get('descriptor', {})
                desc2 = info2.get('descriptor', {})
                if desc1 or desc2:
                    print(f"\n    Descriptor:")
                    for key in ['type', 'sample_rate', 'length', 'channels',
                                'audio_sampling_rate', 'quantization_bits', 'has_summary']:
                        val1 = desc1.get(key, 'N/A')
                        val2 = desc2.get(key, 'N/A')
                        match = "✓" if str(val1) == str(val2) else "⚠️"
                        print(f"      {key}: {match} {val1} vs {val2}")

                    if desc1.get('has_summary') or desc2.get('has_summary'):
                        sl1 = desc1.get('summary_length', 'N/A')
                        sl2 = desc2.get('summary_length', 'N/A')
                        match = "✓" if sl1 == sl2 else "⚠️"
                        print(f"      summary_length: {match} {sl1} vs {sl2}")

                    # 比较 Locator
                    loc1 = desc1.get('locators', [])
                    loc2 = desc2.get('locators', [])
                    if loc1 or loc2:
                        print(f"\n      Locators: {len(loc1)} vs {len(loc2)}")
                        for url1, url2 in zip(loc1, loc2):
                            url1_short = url1.split('/')[-1] if url1 else None
                            url2_short = url2.split('/')[-1] if url2 else None
                            match = "✓" if url1_short == url2_short else "⚠️"
                            print(f"        {match} ...{url1_short} vs ...{url2_short}")


if __name__ == '__main__':
    correct_path = "correct_timeline.aaf"
    test_path = "test_output.aaf"

    try:
        compare_aaf_files(correct_path, test_path)
    except FileNotFoundError as e:
        print(f"错误：找不到文件 - {e}")
        print(f"\n请确认文件路径是否正确")
