import sys
import re
import argparse
from pathlib import Path

# 文字列サイズをバイト数に変換する関数
# @param size_str: '[ 10.5 MB]' のような文字列
# @return: バイト数値
def parse_size_to_bytes(size_str):
    match = re.search(r'([\d.]+)\s*(B|KB|MB|GB|TB)', size_str)
    if not match:
        return 0
    
    value = float(match.group(1))
    unit = match.group(2)
    
    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
    return int(value * multipliers[unit])

# バイト数を読みやすい形式に変換する関数
# @param size_bytes: バイト数値
# @return: '+10.5 MB' のような文字列
def format_bytes(size_bytes):
    if size_bytes == 0: return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size_bytes >= 1024 and i < len(units)-1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:+.1f} {units[i]}"

# スナップショットファイルを読み込み、辞書形式に変換する関数
# @param file_path: スナップショットファイルのパス
# @return: { 'フルパス': バイトサイズ } の辞書
def load_snapshot(file_path):
    snapshot = {}
    path_stack = [] # 現在の階層を保持
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 最初の2行（ヘッダー）をスキップ
            lines = f.readlines()[2:]
            
            for line in lines:
                if not line.strip(): continue
                
                # サイズ部分とツリー部分を分離
                size_part = line[:12]
                tree_part = line[12:].rstrip()
                
                # インデントから階層（深さ）を判定
                # 前日のツールは4スペース刻みなので、空白数をカウント
                indent_content = tree_part.replace('├── ', '    ').replace('└── ', '    ').replace('│   ', '    ')
                indent_count = (len(indent_content) - len(indent_content.lstrip(' '))) // 4
                
                name = tree_part.replace('├── ', '').replace('└── ', '').replace('│   ', '').strip()
                size_bytes = parse_size_to_bytes(size_part)
                
                # スタックを現在の深さに調整
                path_stack = path_stack[:indent_count]
                path_stack.append(name)
                
                full_path = "/".join(path_stack)
                snapshot[full_path] = size_bytes
                
        return snapshot
    except Exception as e:
        print(f"エラー: ファイルの読み込みに失敗しました ({file_path}): {e}")
        sys.exit(1)

# メイン処理
# return: None
def main():
    parser = argparse.ArgumentParser(description="2つのファイルツリー・スナップショットを比較します")
    parser.add_argument("old_file", help="比較元のファイル (旧)")
    parser.add_argument("new_file", help="比較先のファイル (新)")
    args = parser.parse_args()

    old_snap = load_snapshot(args.old_file)
    new_snap = load_snapshot(args.new_file)

    added = []
    removed = []
    changed = []

    # 全てのキー（パス）を取得
    all_paths = sorted(set(old_snap.keys()) | set(new_snap.keys()))

    for path in all_paths:
        if path not in old_snap:
            added.append((path, new_snap[path]))
        elif path not in new_snap:
            removed.append((path, old_snap[path]))
        else:
            diff = new_snap[path] - old_snap[path]
            if diff != 0:
                changed.append((path, diff, new_snap[path]))

    # 結果をファイルに出力
    output_name = f"diff_{Path(args.old_file).stem}_vs_{Path(args.new_file).stem}.txt"
    
    with open(output_name, "w", encoding="utf-8") as f:
        f.write(f"📊 Comparison: {args.old_file} -> {args.new_file}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"🆕 ADDED ({len(added)})\n")
        f.write("-" * 30 + "\n")
        for p, s in added:
            f.write(f"[+{format_bytes(s).strip()}]  {p}\n")
        
        f.write(f"\n🗑️ REMOVED ({len(removed)})\n")
        f.write("-" * 30 + "\n")
        for p, s in removed:
            f.write(f"[-{format_bytes(s).strip()}]  {p}\n")

        f.write(f"\n🔄 SIZE CHANGED ({len(changed)})\n")
        f.write("-" * 30 + "\n")
        for p, d, s in changed:
            f.write(f"[{format_bytes(d):>10}] (Current: {format_bytes(s).strip():>8})  {p}\n")

    print(f"✨ 差分解析が完了しました！")
    print(f"📄 出力結果: {output_name}")

if __name__ == "__main__":
    main()