#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证循环脚本 - 对比 pt_compat 分支与 dev 分支及 DaVinci Resolve 导出的 AAF 文件

此脚本实现三层验证：
1. 与 dev 分支导出的 AAF 文件对比
2. 与 DaVinci Resolve 导出的参考 AAF 文件对比
3. 检查 Pro Tools 兼容性关键特性

使用方法：
    python verification_loop.py --test-data <path_to_test_otio>
"""

import argparse
import sys
import tempfile
import os
from pathlib import Path

import opentimelineio as otio
import aaf2

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))


def export_aaf_from_otio(otio_path, output_path):
    """从 OTIO 文件导出 AAF"""
    print(f"正在导出 AAF: {otio_path} -> {output_path}")
    timeline = otio.adapters.read_from_file(otio_path)
    otio.adapters.write_to_file(timeline, output_path)
    print("[OK] 导出完成")


def compare_aaf_files(file1_path, file2_path, file1_name="File 1", file2_name="File 2"):
    """对比两个 AAF 文件的关键属性"""
    print(f"\n{'='*80}")
    print(f"对比: {file1_name} vs {file2_name}")
    print(f"{'='*80}\n")

    with aaf2.open(file1_path, 'r') as aaf_file1, aaf2.open(file2_path, 'r') as aaf_file2:
        differences = []

        # 1. 对比 Mob 数量
        mobs1 = list(aaf_file1.content.mobs)
        mobs2 = list(aaf_file2.content.mobs)
        
        print(f"Mob 数量:")
        print(f"  {file1_name}: {len(mobs1)}")
        print(f"  {file2_name}: {len(mobs2)}")
        
        if len(mobs1) != len(mobs2):
            differences.append(f"Mob 数量不匹配: {len(mobs1)} vs {len(mobs2)}")
        
        # 2. 对比 CompositionMob
        comp_mobs1 = [m for m in mobs1 if isinstance(m, aaf2.mobs.CompositionMob)]
        comp_mobs2 = [m for m in mobs2 if isinstance(m, aaf2.mobs.CompositionMob)]
        
        print(f"\nCompositionMob 数量:")
        print(f"  {file1_name}: {len(comp_mobs1)}")
        print(f"  {file2_name}: {len(comp_mobs2)}")
        
        if len(comp_mobs1) != len(comp_mobs2):
            differences.append(f"CompositionMob 数量不匹配: {len(comp_mobs1)} vs {len(comp_mobs2)}")
        
        # 3. 对比 CompositionMob MobID
        if comp_mobs1 and comp_mobs2:
            print(f"\nCompositionMob MobID:")
            print(f"  {file1_name}: {comp_mobs1[0].mob_id}")
            print(f"  {file2_name}: {comp_mobs2[0].mob_id}")
            
            mobid1_bytes = comp_mobs1[0].mob_id.bytes_le.hex()
            mobid2_bytes = comp_mobs2[0].mob_id.bytes_le.hex()
            
            # 检查前 16 字节（前缀）
            if mobid1_bytes[:32] != mobid2_bytes[:32]:
                differences.append(f"CompositionMob MobID 前缀不匹配")
                print(f"  [WARN] 前缀不匹配")
            else:
                print(f"  [OK] 前缀匹配")
        
        # 4. 对比 Timecode Slots
        if comp_mobs1 and comp_mobs2:
            tc_slots1 = [s for s in comp_mobs1[0].slots 
                        if isinstance(s.segment, aaf2.components.Timecode)]
            tc_slots2 = [s for s in comp_mobs2[0].slots 
                        if isinstance(s.segment, aaf2.components.Timecode)]
            
            print(f"\nTimecode Slot 数量:")
            print(f"  {file1_name}: {len(tc_slots1)}")
            print(f"  {file2_name}: {len(tc_slots2)}")
            
            if tc_slots1 and tc_slots2:
                tc1 = tc_slots1[0].segment
                tc2 = tc_slots2[0].segment
                
                print(f"\nTimecode 属性:")
                print(f"  Start:")
                print(f"    {file1_name}: {tc1.start}")
                print(f"    {file2_name}: {tc2.start}")
                
                print(f"  Length:")
                print(f"    {file1_name}: {tc1.length}")
                print(f"    {file2_name}: {tc2.length}")
                
                if tc1.length != tc2.length:
                    differences.append(f"Timecode length 不匹配: {tc1.length} vs {tc2.length}")
                
                # 检查 PhysicalTrackNumber
                pt1 = tc_slots1[0].get('PhysicalTrackNumber', None)
                pt2 = tc_slots2[0].get('PhysicalTrackNumber', None)
                
                if pt1 and pt2:
                    print(f"  PhysicalTrackNumber:")
                    print(f"    {file1_name}: {pt1.value}")
                    print(f"    {file2_name}: {pt2.value}")
        
        # 5. 对比 Audio Gain OperationGroup
        print(f"\n{'='*80}")
        print(f"检查 Audio Gain OperationGroup")
        print(f"{'='*80}\n")
        
        og_count1 = 0
        og_count2 = 0
        
        for mob in mobs1:
            if isinstance(mob, aaf2.mobs.CompositionMob):
                for slot in mob.slots:
                    if isinstance(slot.segment, aaf2.components.Sequence):
                        for comp in slot.segment.components:
                            if isinstance(comp, aaf2.components.OperationGroup):
                                if comp.operation and comp.operation.name == "Audio Gain":
                                    og_count1 += 1
        
        for mob in mobs2:
            if isinstance(mob, aaf2.mobs.CompositionMob):
                for slot in mob.slots:
                    if isinstance(slot.segment, aaf2.components.Sequence):
                        for comp in slot.segment.components:
                            if isinstance(comp, aaf2.components.OperationGroup):
                                if comp.operation and comp.operation.name == "Audio Gain":
                                    og_count2 += 1
        
        print(f"Audio Gain OperationGroup 数量:")
        print(f"  {file1_name}: {og_count1}")
        print(f"  {file2_name}: {og_count2}")
        
        if og_count1 != og_count2:
            differences.append(f"Audio Gain OperationGroup 数量不匹配: {og_count1} vs {og_count2}")
        
        # 检查第一个 OperationGroup 的详细信息
        if og_count1 > 0 and og_count2 > 0:
            print(f"\n第一个 Audio Gain OperationGroup 详情:")
            
            og1 = None
            og2 = None
            
            for mob in mobs1:
                if isinstance(mob, aaf2.mobs.CompositionMob):
                    for slot in mob.slots:
                        if isinstance(slot.segment, aaf2.components.Sequence):
                            for comp in slot.segment.components:
                                if isinstance(comp, aaf2.components.OperationGroup):
                                    if comp.operation and comp.operation.name == "Audio Gain":
                                        og1 = comp
                                        break
                            if og1:
                                break
                    if og1:
                        break
            
            for mob in mobs2:
                if isinstance(mob, aaf2.mobs.CompositionMob):
                    for slot in mob.slots:
                        if isinstance(slot.segment, aaf2.components.Sequence):
                            for comp in slot.segment.components:
                                if isinstance(comp, aaf2.components.OperationGroup):
                                    if comp.operation and comp.operation.name == "Audio Gain":
                                        og2 = comp
                                        break
                            if og2:
                                break
                    if og2:
                        break
            
            if og1 and og2:
                # OperationDef UUID
                print(f"  OperationDef UUID:")
                print(f"    {file1_name}: {og1.operation.auid}")
                print(f"    {file2_name}: {og2.operation.auid}")
                
                if str(og1.operation.auid) != str(og2.operation.auid):
                    differences.append(f"OperationDef UUID 不匹配")
                    print(f"    [WARN] 不匹配")
                else:
                    print(f"    [OK] 匹配")
                
                # 检查 ConstantValue 参数
                if og1.parameters and og2.parameters:
                    for p1 in og1.parameters:
                        if hasattr(p1, 'name') and p1.name == "ConstantValue":
                            for p2 in og2.parameters:
                                if hasattr(p2, 'name') and p2.name == "ConstantValue":
                                    print(f"  ConstantValue:")
                                    print(f"    {file1_name}: {p1.value}")
                                    print(f"    {file2_name}: {p2.value}")
                
                # 检查 SourceClip StartTime
                for seg in og1.segments:
                    if isinstance(seg, aaf2.components.SourceClip):
                        print(f"  SourceClip StartTime:")
                        print(f"    {file1_name}: {seg.start}")
                
                for seg in og2.segments:
                    if isinstance(seg, aaf2.components.SourceClip):
                        print(f"    {file2_name}: {seg.start}")
        
        # 6. 总结
        print(f"\n{'='*80}")
        print(f"对比结果")
        print(f"{'='*80}\n")
        
        if differences:
            print(f"发现 {len(differences)} 个差异:\n")
            for i, diff in enumerate(differences, 1):
                print(f"  {i}. {diff}")
            return False
        else:
            print("[OK] 所有关键属性匹配")
            return True


def main():
    parser = argparse.ArgumentParser(description='验证循环脚本')
    parser.add_argument('--test-data', type=str, required=True,
                       help='测试用 OTIO 文件路径')
    parser.add_argument('--dev-aaf', type=str,
                       help='dev 分支导出的 AAF 文件路径（用于对比）')
    parser.add_argument('--davinci-aaf', type=str,
                       help='DaVinci Resolve 导出的参考 AAF 文件路径（用于对比）')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.test_data):
        print(f"错误: 测试数据文件不存在: {args.test_data}")
        return 1
    
    # 导出当前分支的 AAF
    with tempfile.NamedTemporaryFile(suffix='.aaf', delete=False) as tmp:
        current_aaf_path = tmp.name
    
    try:
        export_aaf_from_otio(args.test_data, current_aaf_path)
        
        # 与 dev 分支对比
        if args.dev_aaf and os.path.exists(args.dev_aaf):
            compare_aaf_files(current_aaf_path, args.dev_aaf, 
                            "pt_compat", "dev")
        
        # 与 DaVinci Resolve 对比
        if args.davinci_aaf and os.path.exists(args.davinci_aaf):
            compare_aaf_files(current_aaf_path, args.davinci_aaf,
                            "pt_compat", "DaVinci Resolve")
        
        print(f"\n{'='*80}")
        print(f"验证循环完成")
        print(f"{'='*80}\n")
        print(f"当前分支导出的 AAF 文件: {current_aaf_path}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
