#!/usr/bin/env python
"""
逐字节对比 correct 和 test 两个 AAF 文件
找出所有不同的地方，特别是那些可能影响采样率计算的属性
"""

import struct

def compare_files_binary(correct_path, test_path):
    with open(correct_path, 'rb') as f:
        correct_data = f.read()
    with open(test_path, 'rb') as f:
        test_data = f.read()
    
    print(f"Correct 文件大小：{len(correct_data)} ({len(correct_data):#x})")
    print(f"Test 文件大小：{len(test_data)} ({len(test_data):#x})")
    print()
    
    # 找出所有不同的位置
    differences = []
    min_len = min(len(correct_data), len(test_data))
    
    for i in range(min_len):
        if correct_data[i] != test_data[i]:
            differences.append(i)
    
    # 如果文件长度不同，追加的部分也算差异
    max_len = max(len(correct_data), len(test_data))
    if len(correct_data) != len(test_data):
        for i in range(min_len, max_len):
            differences.append(i)
    
    print(f"不同的字节数：{len(differences)} / {min_len}")
    print(f"差异比例：{len(differences) / min_len * 100:.2f}%")
    print()
    
    if not differences:
        print("两个文件完全相同！")
        return
    
    # 分组显示差异（连续的差异算作一组）
    groups = []
    current_group = [differences[0]]
    
    for i in range(1, len(differences)):
        if differences[i] == differences[i-1] + 1:
            current_group.append(differences[i])
        else:
            groups.append(current_group)
            current_group = [differences[i]]
    groups.append(current_group)
    
    print(f"差异组数：{len(groups)}")
    print()
    
    # 显示前 20 组差异
    for i, group in enumerate(groups[:20]):
        start = group[0]
        end = group[-1]
        length = len(group)
        
        print(f"\n差异组 {i+1}: 偏移 0x{start:08X} - 0x{end:08X} ({length} 字节)")
        
        # 显示 correct 的值
        context_start = max(0, start - 8)
        context_end = min(len(correct_data), end + 8)
        
        print(f"  Correct: {correct_data[context_start:context_end].hex()}")
        print(f"  Test:    {test_data[context_start:context_end].hex()}")
        
        # 标记差异位置
        marker = ' ' * (start - context_start)
        for j in range(length):
            if j < length - 1 and group[j+1] == group[j] + 1:
                marker += '^'
            else:
                marker += '^'
                if j < length - 1:
                    marker += ' ' * (group[j+1] - group[j] - 1)
        print(f"  差异：   {marker}")
        
        # 尝试解析这个差异可能是什么
        if length == 1:
            # 单字节差异
            c_val = correct_data[start]
            t_val = test_data[start]
            print(f"  Correct[{start:#x}] = {c_val:#04x} = {c_val}")
            print(f"  Test[{start:#x}]    = {t_val:#04x} = {t_val}")
            
            # 检查 test 是否是 30 (0x1E)
            if t_val == 0x1E:
                print(f"  ⚠️  Test 是 30 (0x1E)！")
        
        elif length == 4:
            # 4 字节差异，可能是 uint32 或 float
            c_u32 = struct.unpack('<I', correct_data[start:start+4])[0]
            t_u32 = struct.unpack('<I', test_data[start:start+4])[0]
            print(f"  Correct: uint32 = {c_u32} ({c_u32:#x})")
            print(f"  Test:    uint32 = {t_u32} ({t_u32:#x})")
            
            # 检查是否是 Rational 的一部分
            if start + 4 < len(test_data):
                c_rat = struct.unpack('<II', correct_data[start:start+8])
                t_rat = struct.unpack('<II', test_data[start:start+8])
                print(f"  Correct: Rational = {c_rat[0]}/{c_rat[1]} = {c_rat[0]/c_rat[1]}")
                print(f"  Test:    Rational = {t_rat[0]}/{t_rat[1]} = {t_rat[0]/t_rat[1]}")
                
                if t_rat[0] == 30:
                    print(f"  ⚠️  Test 的 Rational numerator 是 30！")
        
        elif length == 8:
            # 8 字节差异，可能是 Rational
            c_rat = struct.unpack('<II', correct_data[start:start+8])
            t_rat = struct.unpack('<II', test_data[start:start+8])
            print(f"  Correct: Rational = {c_rat[0]}/{c_rat[1]} = {c_rat[0]/c_rat[1]}")
            print(f"  Test:    Rational = {t_rat[0]}/{t_rat[1]} = {t_rat[0]/t_rat[1]}")
            
            if t_rat[0] == 30:
                print(f"  ⚠️  Test 的 Rational numerator 是 30！")
            if t_rat[1] == 30:
                print(f"  ⚠️  Test 的 Rational denominator 是 30！")

if __name__ == '__main__':
    correct_file = "correct_timeline.aaf"
    test_file = "test_output.aaf"
    
    print("="*80)
    print("逐字节对比 AAF 文件")
    print("="*80)
    
    compare_files_binary(correct_file, test_file)
