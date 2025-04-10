#!/bin/bash

# Step 1: Conda 环境初始化（使用 CONDA_BASE_PATH 环境变量）
if [[ -z "$CONDA_BASE_PATH" ]]; then
  echo "错误：未设置 CONDA_BASE_PATH 环境变量。请设置为你的 conda 安装路径（例如 /opt/miniconda3）"
  exit 1
fi

if [ -f "${CONDA_BASE_PATH}/etc/profile.d/conda.sh" ]; then
  . "${CONDA_BASE_PATH}/etc/profile.d/conda.sh"
else
  echo "错误：无法在 ${CONDA_BASE_PATH} 下找到 conda.sh，请检查 CONDA_BASE_PATH 是否正确"
  exit 1
fi

conda activate spleeter || { echo "激活 spleeter 环境失败"; exit 1; }

# Step 2: 切换目录（使用 SPLEETER_PATH 环境变量）
if [[ -z "$SPLEETER_PATH" ]]; then
  echo "错误：未设置 SPLEETER_PATH 环境变量。请设置为你 spleeter 项目的根目录。"
  exit 1
fi

cd "$SPLEETER_PATH" || { echo "切换到 SPLEETER_PATH 失败：$SPLEETER_PATH"; exit 1; }

# Step 3: 输入音频路径
audiopath="$1"
if [ ! -f "$audiopath" ]; then
  echo "音频文件不存在: $audiopath"
  exit 1
fi

# 获取音频文件的目录和文件名
audiodir=$(dirname "$audiopath")
audiofilename=$(basename "$audiopath")
filename_wo_ext="${audiofilename%.*}"

# Step 4: 创建 output 文件夹
audiooutputpath="${audiodir}/output"
mkdir -p "$audiooutputpath"

# Step 5: 执行 spleeter 分离
spleeter separate -p spleeter:2stems -o "$audiooutputpath" -d 9999 "$audiopath"

# Step 6: 获取分离后的人声路径
subdir="${audiooutputpath}/${filename_wo_ext}"
vocalspath=$(find "$subdir" -type f -iname "vocals.*" | head -n 1)

if [ ! -f "$vocalspath" ]; then
  echo "未找到人声文件"
  exit 1
fi

# Step 7: 重命名并移动文件
vocal_ext="${vocalspath##*.}"
finalfilename="${filename_wo_ext}-output.${vocal_ext}"
finalpath="${audiodir}/${finalfilename}"

mv "$vocalspath" "$finalpath"

# Step 8: 输出最终文件路径
echo "最终人声路径: $finalpath"
