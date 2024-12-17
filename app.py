import streamlit as st
import os
from PIL import Image, ImageDraw
import cv2
import numpy as np
from pdf2image import convert_from_path
import tempfile
import webbrowser
from pathlib import Path

def highlight_differences(base_pdf_path, check_pdf_path, output_path):
    """PDFの差分を検出し、強調表示する関数"""
    # PDFを画像に変換
    base_images = convert_from_path(
        base_pdf_path, 
        size=(2000, None),
        fmt='png'
    )
    check_images = convert_from_path(
        check_pdf_path,
        size=(2000, None),
        fmt='png'
    )
    
    # 最初のページで処理
    base_image = base_images[0]
    check_image = check_images[0]
    
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
    
    # 差分の閾値処理
    _, diff_mask = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    
    # ベース画像をRGBAに変換
    base_rgba = base_image_resized.convert('RGBA')
    
    # 差分オーバーレイ作成
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
    
    # 白背景の作成
    background = Image.new('RGBA', base_rgba.size, (255, 255, 255, 255))
    
    # レイヤーの合成
    result = Image.alpha_composite(background, base_rgba)
    result = Image.alpha_composite(result, overlay)
    
    # 保存
    result = result.convert('RGB')
    result.save(output_path, 'PNG', quality=95)
    
    return output_path

def main():
    st.title("PDF差分比較ツール")
    
    # ファイルアップロード
    st.subheader("1. PDFファイルを選択してください")
    base_file = st.file_uploader("ベースPDFファイル", type=['pdf'])
    check_file = st.file_uploader("チェック対象PDFファイル", type=['pdf'])
    
    # 出力先フォルダの選択
    st.subheader("2. 出力先フォルダを選択してください")
    output_dir = st.text_input("出力先フォルダのパス", value=str(Path.home() / "Downloads"))
    
    if st.button("差分を検出"):
        if base_file and check_file and output_dir:
            try:
                # 一時ファイルとして保存
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_base:
                    tmp_base.write(base_file.getvalue())
                    base_path = tmp_base.name
                    
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_check:
                    tmp_check.write(check_file.getvalue())
                    check_path = tmp_check.name
                
                # 出力ファイル名の生成
                output_filename = f"diff_result_{base_file.name}_{check_file.name}.png"
                output_path = os.path.join(output_dir, output_filename)
                
                # 差分検出実行
                result_path = highlight_differences(base_path, check_path, output_path)
                
                # 一時ファイルの削除
                os.unlink(base_path)
                os.unlink(check_path)
                
                # 結果ファイルを開く
                webbrowser.open(f'file://{result_path}')
                
                st.success(f"差分検出が完了しました！\n結果ファイル: {output_path}")
                
                # 結果のプレビュー表示
                result_image = Image.open(output_path)
                st.image(result_image, caption="差分検出結果", use_column_width=True)
                
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
        else:
            st.warning("すべての項目を入力してください。")

if __name__ == "__main__":
    main()