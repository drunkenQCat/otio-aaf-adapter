#!/usr/bin/env python
"""枚举 AAF 文件中的所有关键属性，用于 Phase 1 诊断基线。"""

import aaf2
import sys


def enumerate_all_properties(filepath):
    """枚举 AAF 文件中的所有关键属性"""
    with aaf2.open(filepath) as f:
        # === L1: Header 层 ===
        print("=== L1: HEADER ===")
        print(f"  Version: {f.header.get('Version', 'N/A')}")
        print(f"  ObjectModelVersion: {f.header.get('ObjectModelVersion', 'N/A')}")

        try:
            op = f.header['OperationalPattern'].value
            print(f"  OperationalPattern: {op}")
        except Exception:
            print("  OperationalPattern: NOT SET")

        try:
            ec_list = list(f.header['EssenceContainers'].value)
            print(f"  EssenceContainers: {len(ec_list)}")
            for ec in ec_list:
                try:
                    print(f"    EC: {ec['EssenceContainer'].value}")
                except Exception:
                    print(f"    EC: (unknown)")
        except Exception:
            print("  EssenceContainers: NOT SET")

        print("\n=== L1: IDENTIFICATIONS ===")
        try:
            idents = list(f.header['IdentificationList'].value)
        except Exception:
            idents = []
        print(f"  Count: {len(idents)}")
        for i, ident in enumerate(idents):
            print(f"  [{i}] CompanyName: {ident.get('CompanyName', 'N/A')}")
            print(f"  [{i}] ProductName: {ident.get('ProductName', 'N/A')}")
            print(f"  [{i}] ProductVersionString: {ident.get('ProductVersionString', 'N/A')}")
            print(f"  [{i}] Platform: {ident.get('Platform', 'N/A')}")
            try:
                print(f"  [{i}] ProductID: {ident['ProductID'].value}")
            except Exception:
                print(f"  [{i}] ProductID: N/A")
            try:
                print(f"  [{i}] Date: {ident['Date'].value}")
            except Exception:
                pass
            try:
                print(f"  [{i}] GenerationAUID: {ident['GenerationAUID'].value}")
            except Exception:
                pass
            try:
                pv = ident['ProductVersion'].value
                print(f"  [{i}] ProductVersion: {pv}")
            except Exception:
                pass
            try:
                tv = ident['ToolkitVersion'].value
                print(f"  [{i}] ToolkitVersion: {tv}")
            except Exception:
                pass

        # === L2: Mob 图结构层 ===
        print("\n=== L2: MOBS ===")
        mobs = list(f.content.mobs)
        print(f"  Total Mobs: {len(mobs)}")
        print(f"  Mob type sequence: {[m.__class__.__name__ for m in mobs]}")

        for i, mob in enumerate(mobs):
            mob_type = mob.__class__.__name__
            print(f"\n  --- Mob [{i}] {mob_type} ---")
            print(f"  Name: '{mob.name}'")
            print(f"  MobID: {mob.mob_id}")
            mob_id_str = str(mob.mob_id)
            print(f"  MobID prefix (first 32 hex): {mob_id_str[:47]}")
            print(f"  Slots: {len(list(mob.slots))}")

            for j, slot in enumerate(mob.slots):
                print(f"    Slot [{j}]:")
                print(f"      SlotID: {slot.slot_id}")
                print(f"      EditRate: {slot.edit_rate}")
                try:
                    print(f"      PhysicalTrackNumber: {slot['PhysicalTrackNumber'].value}")
                except Exception:
                    print("      PhysicalTrackNumber: NOT SET")
                try:
                    print(f"      SlotName: '{slot.name}'")
                except Exception:
                    pass

                seg = slot.segment
                print(f"      Segment: {seg.__class__.__name__}")
                if hasattr(seg, 'length'):
                    print(f"        Length: {seg.length}")
                if hasattr(seg, 'start'):
                    print(f"        Start: {seg.start}")
                if hasattr(seg, 'fps'):
                    print(f"        FPS: {seg.fps}")
                if hasattr(seg, 'drop'):
                    print(f"        Drop: {seg.drop}")

                if hasattr(seg, 'components'):
                    comps = list(seg.components)
                    print(f"        Components: {len(comps)}")
                    for k, comp in enumerate(comps):
                        comp_type = comp.__class__.__name__
                        info = f"          [{k}] {comp_type}"
                        if hasattr(comp, 'length'):
                            info += f" Length={comp.length}"
                        if hasattr(comp, 'start_time'):
                            info += f" StartTime={comp.start_time}"
                        if hasattr(comp, 'source_mob_slot_id'):
                            info += f" SourceMobSlotID={comp.source_mob_slot_id}"
                        if hasattr(comp, 'mob') and comp.mob:
                            info += f" SourceMob={comp.mob.__class__.__name__}"
                        print(info)

            # === L3: Descriptor 层 ===
            if hasattr(mob, 'descriptor') and mob.descriptor:
                desc = mob.descriptor
                print(f"    Descriptor: {desc.__class__.__name__}")
                # 枚举所有已设置的属性（不限于已知列表）
                print("    Descriptor properties (all):")
                try:
                    for prop in desc.properties():
                        val = prop.value
                        # 对于 bytes 类型，只显示长度和前 44 字节 hex
                        if isinstance(val, (bytes, bytearray)):
                            print(f"      {prop.name}: ({len(val)} bytes) {val[:44].hex()}")
                        else:
                            print(f"      {prop.name}: {val}")
                except Exception as e:
                    print(f"    (error enumerating properties: {e})")
                    # 回退到已知属性列表
                    for prop_name in ['SampleRate', 'Length', 'AudioSamplingRate',
                                      'Channels', 'QuantizationBits', 'ContainerFormat',
                                      'Summary']:
                        try:
                            val = desc[prop_name].value
                            if isinstance(val, (bytes, bytearray)):
                                print(f"      {prop_name}: ({len(val)} bytes) {val[:44].hex()}")
                            else:
                                print(f"      {prop_name}: {val}")
                        except Exception:
                            pass
                # Locator
                try:
                    locs = list(desc['Locator'].value)
                    print(f"    Locators: {len(locs)}")
                    for loc in locs:
                        print(f"      URL: {loc['URLString'].value}")
                except Exception:
                    pass


if __name__ == "__main__":
    correct_path = sys.argv[1] if len(sys.argv) > 1 else "correct_timeline.aaf"
    test_path = sys.argv[2] if len(sys.argv) > 2 else "test_output.aaf"

    print("=" * 80)
    print(f"FILE: {correct_path}")
    print("=" * 80)
    enumerate_all_properties(correct_path)

    print("\n\n" + "=" * 80)
    print(f"FILE: {test_path}")
    print("=" * 80)
    enumerate_all_properties(test_path)
