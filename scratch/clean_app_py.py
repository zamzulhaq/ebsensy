import re

file_path = r"d:\File Azzam\wab-das\ebsensi apk\app.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Replace tabs with 4 spaces
    new_lines.append(line.replace('\t', '    '))

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Tabs replaced with spaces.")
