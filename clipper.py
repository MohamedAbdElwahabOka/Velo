import subprocess
from pathlib import Path

def process_clip(input_file, output_file, start_time=None, end_time=None, top_text="", bottom_text="", is_short=False, is_gif=False):
    """
    Processes a video file to create a clip, meme, or short.
    Requires ffmpeg in system PATH.
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        return False, "Input file does not exist."
        
    cmd = ['ffmpeg', '-y']
    
    # Trim
    if start_time:
        cmd.extend(['-ss', str(start_time)])
    
    cmd.extend(['-i', str(input_path)])
    
    if end_time:
        # Assuming end_time is absolute time in video, duration is end_time - start_time
        cmd.extend(['-to', str(end_time)])
        
    filters = []
    
    # 9:16 Crop for shorts
    if is_short:
        filters.append("crop=ih*(9/16):ih")
        
    # Text Overlays (Meme format)
    # Using basic Arial or system default font
    if top_text or bottom_text:
        # Escape text for ffmpeg
        def escape_text(t):
            return t.replace("'", "\\'").replace(":", "\\:")
            
        font_settings = "fontcolor=white:fontsize=h/10:borderw=3:bordercolor=black"
        
        if top_text:
            t = escape_text(top_text.upper())
            filters.append(f"drawtext=text='{t}':x=(w-text_w)/2:y=h/10:{font_settings}")
            
        if bottom_text:
            b = escape_text(bottom_text.upper())
            filters.append(f"drawtext=text='{b}':x=(w-text_w)/2:y=h-(h/10)-text_h:{font_settings}")

    if filters:
        cmd.extend(['-vf', ",".join(filters)])
        
    if is_gif:
        # Optimizing GIF creation
        cmd.extend(['-f', 'gif'])
        output_path = output_path.with_suffix('.gif')
    else:
        # MP4 Output
        cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '22', '-c:a', 'aac', '-b:a', '128k'])
        output_path = output_path.with_suffix('.mp4')
        
    cmd.append(str(output_path))
    
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode != 0:
            return False, f"ffmpeg error: {process.stderr}"
        return True, str(output_path)
    except FileNotFoundError:
        return False, "ffmpeg not found. Please ensure ffmpeg is installed and in your system PATH."
    except Exception as e:
        return False, str(e)
