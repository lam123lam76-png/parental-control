import sys
import os

# Add backend_api path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend_api"))

from backend_api.database import SessionLocal, engine
from backend_api import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def create_parent(email: str, password: str):
    # Ensure database tables exist
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        existing = db.query(models.Parent).filter(models.Parent.email == email).first()
        if existing:
            print(f"ℹ️ Email '{email}' đã tồn tại trong hệ thống (ID: {existing.id})!")
            return False

        hashed = pwd_context.hash(password)
        parent = models.Parent(email=email, password_hash=hashed)
        db.add(parent)
        db.commit()
        db.refresh(parent)
        print(f"✅ ĐÃ TẠO TÀI KHOẢN PHỤ HUYNH THÀNH CÔNG!")
        print(f"   - Email: {parent.email}")
        print(f"   - Parent ID: {parent.id}")
        print(f"👉 Bây giờ bạn có thể bàn giao Email và Mật khẩu này cho Phụ huynh Đăng nhập & Ghép nối thiết bị!")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi tạo tài khoản: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        email_arg = sys.argv[1]
        pass_arg = sys.argv[2]
        create_parent(email_arg, pass_arg)
    else:
        print("=== CHƯƠNG TRÌNH TẠO TÀI KHOẢN PHỤ HUYNH ===")
        email_input = input("Nhập Email Phụ huynh: ").strip()
        pass_input = input("Nhập Mật khẩu Phụ huynh: ").strip()
        if email_input and pass_input:
            create_parent(email_input, pass_input)
        else:
            print("❌ Email và mật khẩu không được để trống.")
