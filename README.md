# AIsubTranslate
"AI Subtitle Translator" is an open-source tool leveraging AI for efficient and accurate subtitle translation. It aims to break language barriers in video content, making it accessible globally. Join us to improve entertainment, education, and information accessibility.
“AI Subtitle Translator”是一个开源工具，利用AI技术实现高效准确的字幕翻译。其目标是打破视频内容中的语言障碍，使其可以被全球访问。加入我们，一起提升娱乐、教育和信息的可获取性。
下载之后自行配置OpenAI key

安装python3.9-3.11理论都可行
第一步
pip install -r requirement.txt
第二步
python subTranslate.py

<img width="1315" alt="image" src="https://github.com/kelvinhekelvin12399/AIsubTranslate/assets/135954737/d30a4585-c6ea-4b04-b4e5-9bcbe13f0663">


v 0.1
Supports uploading single or multiple lines of monolingual subtitles (e.g., English subtitles).
Capable of translating into multiple languages, with the option to generate bilingual or monolingual subtitles.
Allows selection of how many lines to translate at once (more lines mean faster speed and better quality, but there might be occasional misalignments with GPT translation, hence an individual line processing approach for unaligned cases).
Offers a choice between speed or quality (speed uses GPT-3.5-turbo, quality uses GPT-4).
Supports adding extra information about the movie to assist AI in better subtitle translation.

v 0.1
支持上传单行或多行的单语言字幕（比如英文字幕）
可以翻译成多国语言，生成时可以选择双语或者单语字幕。
支持选择一次翻译多少排（行数越多速度越快质量越好，但是可能偶发gpt翻译时出现行数无法对其，所以写了一个没有对齐时候的逐行处理）
支持速度或者质量（速度为gpt3.5-turbo 质量为gpt4）
支持添加电影的额外信息帮助AI更好的翻译字幕
