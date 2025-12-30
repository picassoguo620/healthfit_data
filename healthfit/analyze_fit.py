import os
import glob
from fitparse import FitFile
import pandas as pd
import matplotlib.pyplot as plt

# 找到仓库中最新的 .fit 文件（或指定文件名）
fit_files = glob.glob('*.fit')  # 如果有后缀
# 如果没后缀，改成 glob.glob('run_*') 或具体名
if not fit_files:
    print("No .fit file found!")
    exit(1)

fit_path = max(fit_files, key=os.path.getctime)  # 最新文件
print(f"Processing: {fit_path}")

# 解析 FIT
fitfile = FitFile(fit_path)
records = []
for record in fitfile.get_messages('record'):
    data = {field.name: field.value for field in record}
    records.append(data)

df = pd.DataFrame(records)

# 基本处理
df['distance_km'] = df['distance'] / 1000 if 'distance' in df.columns else 0
df['km_segment'] = df['distance_km'].astype(int)
if 'enhanced_speed' in df.columns:
    df['speed_kmh'] = df['enhanced_speed'] * 3.6
elif 'speed' in df.columns:
    df['speed_kmh'] = df['speed'] * 3.6

df['cadence_real'] = df['cadence'] * 2 if 'cadence' in df.columns else None  # Apple Watch 步频×2

# 每公里汇总
segmented = df.groupby('km_segment').agg({
    'heart_rate': 'mean',
    'speed_kmh': 'mean',
    'cadence_real': 'mean',
    'distance_km': 'max'
}).reset_index()
segmented['EF'] = segmented['speed_kmh'] / segmented['heart_rate']
segmented['pace_min_per_km'] = 60 / segmented['speed_kmh']

# 生成图表
fig, axs = plt.subplots(3, 1, figsize=(10, 15))
axs[0].plot(df['distance_km'], df['heart_rate'])
axs[0].set_title('Heart Rate vs Distance')
axs[1].plot(df['distance_km'], df['cadence_real'])
axs[1].set_title('Real Cadence (x2) vs Distance')
axs[2].plot(segmented['km_segment'], segmented['EF'])
axs[2].set_title('EF per KM')

plt.tight_layout()
plt.savefig('analysis_plots.png')

# 生成 Markdown 报告
with open('analysis_report.md', 'w') as f:
    f.write(f"# Analysis for {fit_path}\n\n")
    f.write("## Per KM Summary\n")
    f.write(segmented.round(3).to_markdown(index=False))
    f.write("\n\n![Plots](analysis_plots.png)\n")

print("Analysis complete!")
