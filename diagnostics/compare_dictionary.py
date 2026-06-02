#!/usr/bin/env python
"""对比两个 AAF 文件的 Dictionary（各类 Definition 列表）。"""

import aaf2
import sys


def get_def_name(obj):
    """尝试从 Definition 对象中获取名称"""
    for attr in ['class_name', 'name', 'definition_name']:
        try:
            return getattr(obj, attr)
        except Exception:
            pass
    for key in ['Name', 'DefinitionName', 'ClassName']:
        try:
            return obj[key].value
        except Exception:
            pass
    return str(obj)


def compare_def_list(f1, f2, prop_name):
    """对比两个文件中的某个 Definition 列表"""
    try:
        items1 = list(f1.dictionary[prop_name].value)
    except Exception:
        items1 = []
    try:
        items2 = list(f2.dictionary[prop_name].value)
    except Exception:
        items2 = []

    names1 = set(get_def_name(x) for x in items1)
    names2 = set(get_def_name(x) for x in items2)

    common = names1 & names2
    only_in_correct = names1 - names2
    only_in_test = names2 - names1

    print(f"\n=== {prop_name} ===")
    print(f"  Correct: {len(items1)} 项, Test: {len(items2)} 项")
    print(f"  Common: {len(common)}")
    if only_in_correct:
        print(f"  Only in correct: {len(only_in_correct)}")
        for c in sorted(only_in_correct):
            print(f"    {c}")
    if only_in_test:
        print(f"  Only in test: {len(only_in_test)}")
        for c in sorted(only_in_test):
            print(f"    {c}")
    if not only_in_correct and not only_in_test:
        print(f"  ✓ 完全一致")


def compare_dictionaries(correct_path, test_path):
    with aaf2.open(correct_path) as f1, aaf2.open(test_path) as f2:
        def_names = [
            'ContainerDefinitions',
            'DataDefinitions',
            'OperationDefinitions',
            'ParameterDefinitions',
            'PluginDefinitions',
            'CodecDefinitions',
            'InterpolationDefinitions',
            'KLVDataDefinitions',
            'TaggedValueDefinitions',
        ]

        for name in def_names:
            compare_def_list(f1, f2, name)


if __name__ == "__main__":
    correct_path = sys.argv[1] if len(sys.argv) > 1 else "correct_timeline.aaf"
    test_path = sys.argv[2] if len(sys.argv) > 2 else "test_output.aaf"
    compare_dictionaries(correct_path, test_path)
