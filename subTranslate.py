from openai import OpenAI
import datetime
from tqdm import tqdm
from flask import Flask, request, send_file, render_template
import os
from werkzeug.utils import secure_filename
from flask import jsonify

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['FINISHED_FILES_FOLDER'] = './finished'
ALLOWED_EXTENSIONS = {'srt'}
# 确保目标文件夹存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


client = OpenAI(api_key='sk-xxxxx', base_url="https:/xxxx")


# 检查字幕格式是否正确
def check_subtitle_format(subtitle_text):
    subtitle_blocks = subtitle_text.split('\n\n')
    # 检查每个字幕块
    for index, block in enumerate(subtitle_blocks, start=1):
        lines = block.split('\n')
        if len(lines) < 3:  # 检查是否至少包含序号、时间轴和一行字幕
            print(f"字幕格式不正确，位置：字幕块{index}的附近（缺少序号、时间轴、原文或空行太多）请检查格式，修复后重新上传！")
            return {
                "success": False,
                "message": f"字幕格式不正确，位置：字幕块{index}的附近（缺少序号、时间轴、原文或空行太多）请检查格式，修复后重新上传！"
            }
        if not lines[0].isdigit():  # 检查第一行是否为数字（序号）
            print(f"字幕格式不正确，位置：字幕块{index}的附近（序号不正确）请检查格式，修复后重新上传！")
            return {
                "success": False,
                "message": f"字幕格式不正确，位置：字幕块{index}的附近（序号不正确）请检查格式，修复后重新上传！"
            }
        if '-->' not in lines[1]:  # 检查第二行是否包含时间轴
            print(f"字幕格式不正确，位置：字幕块{index}的附近（缺少时间轴）请检查格式，修复后重新上传！")
            return {
                "success": False,
                "message": f"字幕格式不正确，位置：字幕块{index}的附近（缺少时间轴）请检查格式，修复后重新上传！"
            }
    return {"success": True}


# 每次处理5个字幕块
def process_subtitles(text, batch_size):
    subtitle_blocks = text.split('\n\n')
    processed_batches = []
    # 分批处理字幕
    for batch_start in range(0, len(subtitle_blocks), batch_size):
        batch_blocks = subtitle_blocks[batch_start:batch_start + batch_size]
        processed_batch = []
        for block in batch_blocks:
            lines = block.split('\n')
            subtitle_text = ' '.join(lines[2:])  # 合并每个字幕块的文本为一行
            processed_batch.append(subtitle_text.strip())
        processed_text_for_batch = '\n'.join(processed_batch)  # 使用句尾符将不同块的文本分隔开
        processed_batches.append(processed_text_for_batch)  # 将整个批次的处理后文本添加到列表中
    return processed_batches


# 获取所有完整的处理后的纯英文文本，按行分开
def get_processed_subtitles(text, batch_size):
    subtitle_blocks = text.split('\n\n')
    all_processed_texts = []
    for batch_start in range(0, len(subtitle_blocks), batch_size):
        batch_blocks = subtitle_blocks[batch_start:batch_start + batch_size]
        processed_batch = []
        for block in batch_blocks:
            lines = block.split('\n')
            subtitle_text = ' '.join(lines[2:])  # 合并每个字幕块的文本为一行
            processed_batch.append(subtitle_text.strip())
        processed_text_for_batch = '\n'.join(processed_batch)  # 使用句尾符将不同块的文本分隔开
        all_processed_texts.append(processed_text_for_batch)  # 将整个批次的处理后文本添加到列表中

    # 将所有批次的处理后文本以单个句尾符连接成一个字符串，并返回
    final_processed_text = '\n'.join(all_processed_texts)
    return final_processed_text


current_progress = {
    "current_batch": 0,
    "total_batches": 0,
    "current_original_text": "",
    "current_translated_text": "",
    "current_line_original": "",
    "current_line_translated": ""
}


# 翻译
def translate(text, instruction, batch_size, model, max_retries=3):
    global current_progress
    current_progress = {
        "current_batch": 0,
        "total_batches": 0,
        "current_original_text": "",
        "current_translated_text": "",
        "current_line_original": "",
        "current_line_translated": ""
    }
    retries = 0
    all_translated_texts = []  # 新增列表以保存翻译后的文本
    processed_texts = process_subtitles(text, batch_size)  # 假设process_subtitles返回待翻译批次的列表
    total_batches = len(processed_texts)
    batch_num = 1
    print(instruction)
    for processed_text in tqdm(processed_texts, desc="Translating batches"):
        retries = 0  # 重置重试次数为每个批次准备
        while retries < max_retries:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": processed_text}
                ]
            )
            translated_text = response.choices[0].message.content
            print(f"批次 {batch_num}, 尝试第 {retries + 1} 次- 【原文】:\n{processed_text}")
            print(f"批次 {batch_num}, 尝试第 {retries + 1} 次- 【译文】:\n{translated_text}")
            current_progress["current_batch"] = batch_num
            print(current_progress["current_batch"])
            current_progress["total_batches"] = total_batches
            current_progress["current_original_text"] = processed_text
            current_progress["current_translated_text"] = translated_text
            # 如果翻译后行数不一致
            if translated_text.count('\n') != processed_text.count('\n'):
                retries += 1
                warning_info = f"警告：翻译前后行数不一致，正在对批次{batch_num}的内容逐行翻译..."
                print(warning_info)
                # 对批次中的内容逐行进行翻译
                individual_lines = processed_text.split('\n')
                translated_lines = []

                for line in individual_lines:
                    line_response = client.chat.completions.create(
                        model=model,
                        temperature=0,
                        messages=[
                            {"role": "system", "content": instruction},
                            {"role": "user", "content": line}
                        ]
                    )
                    translated_line = line_response.choices[0].message.content
                    # 如果翻译后的文本包含多行，合并这些行为一行
                    if '\n' in translated_line:
                        # 用空格替换换行符以合并文本为一行
                        translated_line = translated_line.replace('\n', ' ')
                    print(f"逐行处理中 - 原文:\n{line}")
                    print(f"逐行处理 - 译文:\n{translated_line}")
                    # 如果开始逐行处理
                    current_progress["current_line_original"] = line
                    current_progress["current_line_translated"] = translated_line
                    translated_lines.append(translated_line)
                translated_text = '\n'.join(translated_lines)
                all_translated_texts.append(translated_text)
                break  # 跳出重试循环
            else:
                all_translated_texts.append(translated_text)
                break  # 当前批次翻译完成，跳出重试循环

            if retries == max_retries:
                error_info = "错误：达到最大重试次数，翻译失败。"
                print(error_info)
                return ""  # 重试次数用尽还未成功，返回空字符串

        batch_num += 1

    final_translated_text = '\n'.join(all_translated_texts)  # 使用两个换行符分隔不同批次的翻译
    return final_translated_text


# 创建中文字幕
def create_chinese_subtitles(original_text, translated_text):
    # 分割原始字幕和翻译后的文本为单独的块和行
    original_blocks = original_text.split('\n\n')
    translated_lines = translated_text.split('\n')

    chinese_subtitles = []

    for index, block in enumerate(original_blocks):
        # 拆分每个字幕块为单独的行
        lines = block.split('\n')
        # 仅保留字幕块的序号和时间轴
        chinese_block = lines[:2]
        # 插入翻译后的中文文本
        if index < len(translated_lines):
            chinese_block.append(translated_lines[index])
        # 合并为单个字幕块
        chinese_subtitles.append('\n'.join(chinese_block))

    # 合并为完整的中文字幕文本
    return '\n\n'.join(chinese_subtitles)


# 创建双语字幕
def create_bilingual_subtitles(original_text, translated_text, batch_size):
    # 首先创建中文字幕，这将移除原字幕中所有英文
    chinese_subtitles = create_chinese_subtitles(original_text, translated_text)

    # 获取全部处理过的英文字幕
    processed_english_subtitles = get_processed_subtitles(original_text, batch_size)

    # 将中文字幕和处理过的英文字幕分割为块
    chinese_blocks = chinese_subtitles.split('\n\n')
    processed_english_lines = processed_english_subtitles.split('\n')

    bilingual_subtitles = []

    # 遍历每个中文字幕块，并在其下面插入对应的处理过的英文
    for index, block in enumerate(chinese_blocks):
        lines = block.split('\n')
        # 插入翻译后的中文文本
        if index < len(processed_english_lines):
            # 确保在时间轴和翻译的中文下方插入英文
            lines.append(processed_english_lines[index])

        # 合并为单个字幕块
        bilingual_block = '\n'.join(lines)
        bilingual_subtitles.append(bilingual_block)

    # 合并为完整的双语字幕文本
    return '\n\n'.join(bilingual_subtitles)


# 生成字幕
def generate_subtitles(text, subtitle_option, instruction, batch_size, model):
    # 获取翻译后的文本
    translated_text = translate(text, instruction, batch_size, model)
    if subtitle_option == 1:
        # 直接创建双语字幕，因为create_bilingual_subtitles内部会处理英文字幕
        return create_bilingual_subtitles(text, translated_text, batch_size)
    elif subtitle_option == 2:
        # 创建中文字幕
        return create_chinese_subtitles(text, translated_text)
    else:
        print("Invalid option. Please choose a valid subtitle option.")
        return None


# 写入srt文件
def write_subtitles_to_file(subtitles, subtitle_option):
    # 获取当前时间戳
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # 指定保存字幕的目录路径
    directory_path = "./finished/"
    # 检查目录是否存在，不存在则创建
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    # 根据选项设置文件名，包含完整的路径
    filename = f"{directory_path}output_{subtitle_option}_{timestamp}.srt"
    # 写入字幕到文件
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(subtitles)
    return filename


def send_response(status="success", message=None, data=None):
    return jsonify({
        "status": status,
        "message": message,
        "data": data
    })


@app.route('/translation_progress')
def translation_progress():
    return jsonify(current_progress)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload_subtitle', methods=['POST'])
def upload_subtitle():
    if 'subtitleFile' not in request.files:
        return send_response(status="error", message="没有文件被上传。"), 400

    file = request.files['subtitleFile']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"success": False, "message": "没有选择文件或文件类型不正确。"}), 400

    option = request.form.get('option', None)
    language = request.form.get('language', None)
    config = request.form.get('config', None)
    batch_size = int(request.form.get('batchSize', 5))
    model = request.form.get('model', 'gpt-3.5-turbo')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 动态构建instruction字符串
        instruction_template = """
你是一个优秀的电影字幕翻译者，你的工作是将英文电影字幕翻译成{language}。注意翻译的更自然一些，而不是死板的机器翻译，而且可能因为断句导致这一行内容不齐全，你需要结合经验推断可能说的什么。
请注意格式，我发给你的是多少行，翻译完之后断句也得是相同的行数，否则会有严重错误！
---------------------------
{config}
"""
        instruction = instruction_template.format(language=language, config=config)

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            text = f.read().strip()

        # 检查字幕格式
        format_check_result = check_subtitle_format(text)
        if not format_check_result["success"]:
            # 格式检查未通过，返回错误信息
            return jsonify(format_check_result), 400

        subtitle_option = int(option)
        subtitles = generate_subtitles(text, subtitle_option, instruction, batch_size, model)
        if subtitles is not None:
            translated_filename = write_subtitles_to_file(subtitles, subtitle_option)
            return send_file(translated_filename, as_attachment=True)
        else:
            # 生成字幕失败的情况
            return jsonify({"success": False, "message": "字幕生成失败。"}), 500

    return jsonify({"success": True, "message": "文件上传处理完成。"})


if __name__ == '__main__':
    app.run(debug=True, port=5004, host='0.0.0.0')
