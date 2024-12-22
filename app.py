import streamlit as st
import os
from PIL import Image, ImageDraw
import cv2
import numpy as np
from pdf2image import convert_from_path
import tempfile
import datetime
from zipfile import ZipFile
import io

def highlight_differences(base_image, check_image, progress_bar=None, current_progress=0):
    """個別の画像ページの差分を検出する関数"""
    # 画像のリサイズ
    min_width = min(base_image.width, check_image.width)
    min_height = min(base_image.height, check_image.height)
    base_image_resized = base_image.resize((min_width, min_height), Image.LANCZOS)
    check_image_resized = check_image.resize((min_width, min_height), Image.LANCZOS)
    
    # グレースケール変換して差分検出
    base_gray = cv2.cvtColor(np.array(base_image_resized), cv2.COLOR_RGB2GRAY)
    check_gray = cv2.cvtColor(np.array(check_image_resized), cv2.COLOR_RGB2GRAY)
    
    # 差分計算
    diff = cv2.absdiff(base_gray, check_gray)
    _, diff_mask = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    
    # 画像処理
    base_rgba = base_image_resized.convert('RGBA')
    overlay = Image.new('RGBA', base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # 差分部分に下線や枠線を追加
    height, width = diff_mask.shape
    for y in range(height):
        for x in range(width):
            if diff_mask[y, x] > 0:
                draw.point((x, y), fill=(255, 165, 0, 120))
                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                    new_x, new_y = x + dx, y + dy
                    if 0 <= new_x < width and 0 <= new_y < height:
                        draw.point((new_x, new_y), fill=(255, 165, 0, 60))
    
    # 画像の合成
    background = Image.new('RGBA', base_rgba.size, (255, 255, 255, 255))
    result = Image.alpha_composite(background, base_rgba)
    result = Image.alpha_composite(result, overlay)
    result = result.convert('RGB')
    
    return result

def process_pdfs(base_pdf_path, check_pdf_path, progress_bar):
    """全てのPDFページを処理する関数"""
    # PDFを画像に変換
    progress_bar.progress(10, text="PDFを画像に変換中...")
    base_images = convert_from_path(base_pdf_path, size=(2000, None), fmt='png')
    check_images = convert_from_path(check_pdf_path, size=(2000, None), fmt='png')
    
    total_pages = min(len(base_images), len(check_images))
    st.write(f"検出したページ数: {total_pages}")  # ← この行を追加
    st.write(f"ベースPDFのページ数: {len(base_images)}")  # ← この行も追加
    st.write(f"チェック対象PDFのページ数: {len(check_images)}")  # ← この行も追加
    results = []
    
    # 各ページを処理
    for i in range(total_pages):
        progress = int(10 + (80 * i / total_pages))
        progress_bar.progress(progress, text=f"ページ {i+1}/{total_pages} を処理中...")
        
        result_image = highlight_differences(base_images[i], check_images[i])
        results.append(result_image)
    
    progress_bar.progress(100, text="完了！")
    return results

def main():
    st.title("PDF差分比較ツール（複数ページ対応）")
    
    # ファイルアップロード
    st.subheader("1. PDFファイルを選択してください")
    base_file = st.file_uploader("ベースPDFファイル", type=['pdf'])
    check_file = st.file_uploader("チェック対象PDFファイル", type=['pdf'])

    if st.button("差分を検出"):
        if base_file and check_file:
            try:
                # プログレスバーの初期化
                progress_bar = st.progress(0, text="処理を開始します...")
                
                # 一時ファイルとして保存
                progress_bar.progress(5, text="ファイルを準備中...")
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_base:
                    tmp_base.write(base_file.getvalue())
                    base_path = tmp_base.name
                    
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_check:
                    tmp_check.write(check_file.getvalue())
                    check_path = tmp_check.name
                
                # 差分検出実行
                result_images = process_pdfs(base_path, check_path, progress_bar)
                
                # 一時ファイルの削除
                os.unlink(base_path)
                os.unlink(check_path)
                
                # 結果の表示
                st.subheader("差分検出結果")
                for i, img in enumerate(result_images):
                    st.image(img, caption=f"ページ {i+1}", use_column_width=True)
                
                # ZIPファイルの作成
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_buffer = io.BytesIO()
                with ZipFile(zip_buffer, 'w') as zip_file:
                    for i, img in enumerate(result_images):
                        img_buffer = io.BytesIO()
                        img.save(img_buffer, format='PNG')
                        zip_file.writestr(f'diff_result_page_{i+1}.png', img_buffer.getvalue())
                
                # ダウンロードボタン
                st.download_button(
                    label="全ページをダウンロード (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"diff_results_{timestamp}.zip",
                    mime="application/zip"
                )
                
                st.success(f"処理が完了しました！全 {len(result_images)} ページの処理が終了しました。")
                
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
        else:
            st.warning("PDFファイルを両方アップロードしてください。")

if __name__ == "__main__":
    main()