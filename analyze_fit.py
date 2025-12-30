import os
import glob
from fitparse import FitFile
import pandas as pd
import matplotlib.pyplot as plt

# 查找 healthfit 文件夹下最新的文件（按修改时间）
fit_dir = 'healthfit'
if not os.path.exists(fit_dir):
    print("healthfit folder not found!")
    exit(1)

# 获取所有文件，按修改时间倒序
files = glob.glob(os.path.join(fit_dir, '*'))
if not files:
    print("No files in healthfit/")
    exit(1)

# 取最新文件（即使没后缀）
latest_file = max(files, key=os.path.getctime)
filename = os.path.basename(latest_file)
print(f"Processing latest file: {filename}")

# 解析 FIT 文件（fitparse 可以处理无后缀文件）
try:
    fitfile = FitFile(latest_file)
except Exception as e:
    print(f"Error parsing file: {e}")
    exit(1)

# 提取 record 数据
records = []
for record in fitfile.get_messages('record'):
    data = {field.name: field.value for field in record}
    records.append(data)

if not records:
    print("No record data found!")
    exit(1)

df = pd.DataFrame(records)

# 数据处理
df['distance_km'] = df['distance'] / 1000 if 'distance' in df.columns else 0
df['km_segment'] = df['distance_km'].astype(int)

if 'enhanced_speed' in df.columns:
    df['speed_kmh'] = df['enhanced_speed'] * 3.6
elif 'speed' in df.columns:
    df['speed_kmh'] = df['speed'] * 3.6
else:
    df['speed_kmh'] = 0

# Apple Watch 步频 ×2
if 'cadence' in df.columns:
    df['cadence_real'] = df['cadence'] * 2

# 每公里汇总
segmented = df.groupby('km_segment').agg({
    'heart_rate': 'mean',
    'speed_kmh': 'mean',
    'cadence_real': 'mean' if 'cadence_real' in df.columns else 'cadence',
    'distance_km': 'max'
}).round(3).reset_index()

segmented['EF'] = (segmented['speed_kmh'] / segmented['heart_rate']).round(4)
segmented['pace_min_per_km'] = (60 / segmented['speed_kmh']).round(2)

# 生成图表
fig, axs = plt.subplots(3, 1, figsize=(12, 12))
axs[0].plot(df['distance_km'], df['heart_rate'], label='Heart Rate')
axs[0].set_title('Heart Rate vs Distance')
axs[0].set_ylabel('BPM')
axs[0].grid(True)

if 'cadence_real' in df.columns:
    axs[1].plot(df['distance_km'], df['cadence_real'], color='orange', label='Cadence (x2)')
else:
    axs[1].plot(df['distance_km'], df['cadence'], color='orange')
axs[1].set_title('Cadence vs Distance')
axs[1].set_ylabel('SPM')
axs[1].grid(True)

axs[2].plot(segmented['km_segment'], segmented['EF'], marker='o')
axs[2].set_title('Efficiency Factor (EF) per KM')
axs[2].set_xlabel('KM Segment')
axs[2].grid(True)

plt.tight_layout()
plt.savefig('analysis_plots.png', dpi=150)
plt.close()

# 生成报告
with open('analysis_report.md', 'w', encoding='utf-8') as f:
    f.write(f"# 最新跑步分析报告\n\n")
    f.write(f"**文件**: {filename}\n\n")
    f.write(f"**总距离**: {df['distance_km'].max():.2f} km\n")
    f.write(f"**平均心率**: {df['heart_rate'].mean():.1f} bpm\n")
    f.write(f"**平均步频**: {df['cadence_real'].mean() if 'cadence_real' in df.columns else df['cadence'].mean():.1f} spm\n\n")
    f.write("## 每公里数据\n\n")
    f.write(segmented.to_markdown(index=False))
    f.write("\n\n![分析图表](analysis_plots.png)\n")

print("分析完成！报告和图表已生成。")
