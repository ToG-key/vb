import os
import sys
import struct
import random
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


MIN_RAC = 20 * 1024 * 1024      
MAX_RAC = 250 * 1024 * 1024     

def get_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_file(file_path, password):
    with open(file_path, "rb") as f:
        original_data = f.read()
        
    if len(original_data) == 0:
        raise ValueError("File rỗng.")

    salt = os.urandom(16)
    key = get_key(password, salt)
    fernet = Fernet(key)
    
    encrypted_data = fernet.encrypt(original_data)
    padding_size = random.randint(MIN_RAC, MAX_RAC)
    half_junk = padding_size // 2
    
    header = struct.pack("<II", half_junk, len(encrypted_data)) + salt
    save_path = file_path + ".enc"
    
    # Ghi file siêu tốc (Sparse)
    with open(save_path, "wb") as f:
        f.write(header)
        f.seek(24 + half_junk)
        f.write(encrypted_data)
        
        current_pos = f.tell()
        target_end = 24 + padding_size + len(encrypted_data)
        if target_end > current_pos:
            f.seek(target_end - 1)
            f.write(b'\0') 
        
    if os.path.exists(save_path):
        os.remove(file_path) 
        return save_path

def decrypt_file(file_path, password):
    with open(file_path, "rb") as f:
        header = f.read(24)
        junk_len_1, enc_data_len = struct.unpack("<II", header[:8])
        salt = header[8:24]
        
        start_pos = 24 + junk_len_1
        f.seek(start_pos)
        encrypted_data = f.read(enc_data_len)
        
    try:
        key = get_key(password, salt)
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)
        
        save_path = file_path[:-4] 
        if os.path.exists(save_path):
            save_path = save_path + "_decrypted" + os.path.splitext(save_path)[1]
            
        with open(save_path, "wb") as f:
            f.write(decrypted_data)
            
        if os.path.exists(save_path):
            os.remove(file_path) 
            return save_path
            
    except Exception:
        raise ValueError("Sai pass hoặc file hỏng!")

def process_all_files(action, password, script_name):
    current_dir = os.getcwd()
    files = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]
    
    # Lọc danh sách file hợp lệ để đếm tổng số (n)
    if action == "1":
        valid_files = [f for f in files if f != script_name and not f.endswith(".enc")]
    elif action == "2":
        valid_files = [f for f in files if f.endswith(".enc")]
    else:
        valid_files = []

    total = len(valid_files)
    count_success = 0
    count_error = 0

    for index, filename in enumerate(valid_files, start=1):
        # Chỉ in tiến trình n/n (dùng \r để ghi đè lên dòng cũ, tạo cảm giác mượt mà)
        print(f"\r{index}/{total}", end="", flush=True)
        
        file_path = os.path.join(current_dir, filename)
        try:
            if action == "1":
                encrypt_file(file_path, password)
            elif action == "2":
                decrypt_file(file_path, password)
            count_success += 1
        except Exception:
            count_error += 1

    # Xuống dòng sau khi chạy xong
    if total > 0:
        print() 

def main():
    if len(sys.argv) != 4:
        sys.exit(1)
        
    action = sys.argv[1]
    target = sys.argv[2]
    password = sys.argv[3]
    script_name = os.path.basename(sys.argv[0])
    
    if target.lower() == "all":
        process_all_files(action, password, script_name)
        
        if action == "1":
            try:
                script_path = os.path.abspath(sys.argv[0])
                if os.path.exists(script_path):
                    os.remove(script_path)
            except:
                pass
                
    else:
        if not os.path.exists(target):
            sys.exit(1)
        try:
            if action == "1":
                print("1/1", end="", flush=True)
                encrypt_file(target, password)
                print()
                
                try:
                    script_path = os.path.abspath(sys.argv[0])
                    if os.path.exists(script_path):
                        os.remove(script_path)
                except:
                    pass
                    
            elif action == "2":
                print("1/1", end="", flush=True)
                decrypt_file(target, password)
                print()
        except Exception:
            sys.exit(1)

if __name__ == "__main__":
    main()
