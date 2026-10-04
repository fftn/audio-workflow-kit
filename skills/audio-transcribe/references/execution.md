# 参数与执行

faster-whisper 历史基线：large-v3，CUDA／float16，beam_size=5，best_of=5，temperature=[0,0.2,0.4,0.6,0.8,1]，VAD=true，min_silence_duration_ms=450，condition_on_previous_text=false。不默认传 hotwords 或 initial_prompt。

Sortformer 历史配置：chunk_len=340，chunk_right_context=40，fifo_len=40，speaker_cache_update_period=300，speaker_cache_len=188，batch_size=1。这是离线长素材复现配置，存在较大输入缓冲延迟，不代表低延迟实时语音方案。[模型卡](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2.1)

准备接收方自己的兼容环境：ASR worker 需要 faster-whisper；分离 worker 需要 CUDA、PyTorch、NeMo ASR 及匹配的模型权重。FFmpeg 用于解码和副本处理。将实际版本写入运行记录，不把当前安装版本硬编码成永远通用的要求。

示例相对路径完全属于接收方输入：

```bash
python3 scripts/asr.py --audio input/sample.wav --out-dir runs/sample --dry-run
python3 scripts/asr.py --audio input/sample.wav --out-dir runs/sample --device cuda --compute-type float16
python3 scripts/diarize.py --audio input/sample.wav --output runs/sample/diarization.json --dry-run
python3 scripts/align_speakers.py --asr runs/sample/raw.json --diar runs/sample/diarization.json --output runs/sample/diarized.json
```

脚本没有自动远端上传器或自动删除器。若迁移到接收方的自托管服务器，由调用方执行独立目录、哈希和精确清理约束。dry-run 仅打印配置；不会下载模型、访问主机或生成转写。

MP3 可用 libmp3lame、VBR quality 2 生成高质量网络副本，核对时长和声道。MP3 是有损编码，不能称为无损。
