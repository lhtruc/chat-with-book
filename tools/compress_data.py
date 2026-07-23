"""
Script nén dữ liệu processed_chunks.json (450MB) thành file processed_chunks.json.gz (~60MB).
Giúp việc push code lên Git, Hugging Face Spaces hoặc Google Cloud Run cực kỳ nhẹ và nhanh chóng.
"""
import os
import gzip
import shutil
import time

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
JSON_PATH = os.path.join(DATA_DIR, "processed_chunks.json")
GZ_PATH = os.path.join(DATA_DIR, "processed_chunks.json.gz")


def compress_chunks():
    if not os.path.exists(JSON_PATH):
        print(f"❌ Không tìm thấy file {JSON_PATH}")
        return

    print(f"📦 Đang nén {JSON_PATH}...")
    start_time = time.time()
    orig_size = os.path.getsize(JSON_PATH) / (1024 * 1024)

    with open(JSON_PATH, "rb") as f_in:
        with gzip.open(GZ_PATH, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)

    compressed_size = os.path.getsize(GZ_PATH) / (1024 * 1024)
    elapsed = time.time() - start_time
    print(f"✅ Hoàn tất nén trong {elapsed:.2f}s!")
    print(f"   • Dung lượng gốc:  {orig_size:.2f} MB")
    print(f"   • Dung lượng nén: {compressed_size:.2f} MB (Giảm {(1 - compressed_size/orig_size)*100:.1f}%)")
    print(f"   • File xuất ra:    {GZ_PATH}")


def decompress_chunks():
    if not os.path.exists(GZ_PATH):
        print(f"❌ Không tìm thấy file {GZ_PATH}")
        return

    print(f"📂 Đang giải nén {GZ_PATH} -> {JSON_PATH}...")
    start_time = time.time()
    with gzip.open(GZ_PATH, "rb") as f_in:
        with open(JSON_PATH, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    elapsed = time.time() - start_time
    print(f"✅ Giải nén thành công trong {elapsed:.2f}s!")


if __name__ == "__main__":
    compress_chunks()
