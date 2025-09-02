# setup_database.py - Script untuk migrasi dari CSV ke SQLite
import sqlite3
import pandas as pd
import os
import re
from datetime import datetime

def create_database():
    """Buat database dan tabel SQLite"""
    conn = sqlite3.connect('dpr_data.db')
    cursor = conn.cursor()
    
    # Buat tabel sesuai struktur data asli
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anggota_dpr (
            id INTEGER PRIMARY KEY,
            anggota INTEGER UNIQUE,
            link_foto TEXT,
            link_profil TEXT,
            nama TEXT NOT NULL,
            fraksi TEXT,
            dapil TEXT,
            akd_clean TEXT,
            ttl TEXT,
            agama TEXT,
            pendidikan TEXT,
            pekerjaan TEXT,
            organisasi TEXT,
            kota_lahir TEXT,
            usia INTEGER,
            pendidikan_terakhir TEXT,
            is_kader TEXT,
            is_dewan TEXT,
            usia_kategori TEXT,
            rank_partai INTEGER,
            partai TEXT,
            pendidikan_clean TEXT,
            organisasi_clean TEXT
        )
    ''')
    
    # Buat index untuk pencarian cepat
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nama ON anggota_dpr(nama)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fraksi ON anggota_dpr(fraksi)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_partai ON anggota_dpr(partai)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dapil ON anggota_dpr(dapil)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kota_lahir ON anggota_dpr(kota_lahir)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agama ON anggota_dpr(agama)')
    
    conn.commit()
    conn.close()
    print("Database dan tabel berhasil dibuat!")

def clean_data(df):
    """Bersihkan data seperti di kode asli"""
    
    def extract_education(edu_text):
        if not edu_text or str(edu_text).strip() == '' or str(edu_text) == 'nan':
            return 'Tidak tersedia'
        
        edu_levels = ['S3', 'S2', 'S1', 'DIPLOMA', 'SMA', 'SMP', 'SD']
        edu_text_upper = str(edu_text).upper()
        
        for level in edu_levels:
            if level in edu_text_upper:
                pattern = rf'{level}[,\s]*([^.]+)'
                match = re.search(pattern, edu_text_upper)
                if match:
                    institution = match.group(1).strip()
                    return f"{level} - {institution}"
                return level
        
        return str(edu_text)[:100] + '...' if len(str(edu_text)) > 100 else str(edu_text)
    
    def extract_organizations(org_text):
        if not org_text or str(org_text).strip() == '' or str(org_text) == 'nan':
            return 'Tidak tersedia'
        
        orgs = re.split(r'[,\d]+\.', str(org_text))
        clean_orgs = []
        
        for org in orgs[:3]:
            org = org.strip()
            if org and len(org) > 5:
                org = re.sub(r'Sebagai:.*?Tahun:.*?\d{4}.*?-.*?\d{0,4}', '', org)
                org = org.strip()
                if org:
                    clean_orgs.append(org)
        
        return ', '.join(clean_orgs) if clean_orgs else str(org_text)[:100]
    
    def extract_birth_city(ttl):
        if not ttl or str(ttl).strip() == '' or str(ttl) == 'nan':
            return 'Tidak tersedia'
        
        if '/' in str(ttl):
            city = str(ttl).split('/')[0].strip()
            return city if city else 'Tidak tersedia'
        
        return str(ttl)
    
    def calculate_age(ttl):
        if not ttl or str(ttl).strip() == '' or str(ttl) == 'nan':
            return None
        
        try:
            if '/' in str(ttl):
                date_part = str(ttl).split('/')[-1].strip()
                date_formats = ['%d %B %Y', '%d %b %Y', '%d-%m-%Y', '%d/%m/%Y']
                
                for fmt in date_formats:
                    try:
                        birth_date = datetime.strptime(date_part, fmt)
                        age = datetime.now().year - birth_date.year
                        return age if age > 0 and age < 100 else None
                    except:
                        continue
        except:
            pass
        
        return None
    
    # Bersihkan nama kolom
    df.columns = [str(col).strip() for col in df.columns]
    
    # Hapus kolom unnamed
    unnamed_cols = [col for col in df.columns if 'Unnamed' in str(col)]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    
    # Fill NaN dengan string kosong
    df = df.fillna('')
    
    # Bersihkan nama
    if 'nama' in df.columns:
        df['nama'] = df['nama'].astype(str).str.replace('"', '').str.strip()
    
    # Proses data pendidikan
    if 'pendidikan' in df.columns:
        df['pendidikan_clean'] = df['pendidikan'].apply(extract_education)
    
    # Proses data organisasi
    if 'organisasi' in df.columns:
        df['organisasi_clean'] = df['organisasi'].apply(extract_organizations)
    
    # Extract kota lahir dari TTL
    if 'ttl' in df.columns:
        if 'kotaLahir' not in df.columns:
            df['kota_lahir'] = df['ttl'].apply(extract_birth_city)
        else:
            # Jika sudah ada kotaLahir, rename saja
            df = df.rename(columns={'kotaLahir': 'kota_lahir'})
    
    # Hitung usia
    if 'usia' not in df.columns and 'ttl' in df.columns:
        df['usia'] = df['ttl'].apply(calculate_age)
    
    # Bersihkan kolom numerik
    if 'Anggota' in df.columns:
        df['anggota'] = pd.to_numeric(df['Anggota'], errors='coerce')
        df = df.dropna(subset=['anggota'])
    
    return df

def import_from_csv(csv_file):
    """Import data dari CSV ke SQLite dengan pembersihan"""
    if not os.path.exists(csv_file):
        print(f"File {csv_file} tidak ditemukan!")
        return False
    
    try:
        # Baca CSV
        print(f"Membaca {csv_file}...")
        df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
        print(f"Data asli: {df.shape[0]} baris, {df.shape[1]} kolom")
        
        # Bersihkan data
        df = clean_data(df)
        print(f"Data setelah dibersihkan: {df.shape[0]} baris")
        
        # Koneksi ke database
        conn = sqlite3.connect('dpr_data.db')
        
        # Pastikan kolom sesuai dengan schema database
        required_columns = [
            'anggota', 'link_foto', 'link_profil', 'nama', 'fraksi', 'dapil',
            'akd_clean', 'ttl', 'agama', 'pendidikan', 'pekerjaan', 'organisasi',
            'kota_lahir', 'usia', 'pendidikan_terakhir', 'is_kader', 'is_dewan',
            'usia_kategori', 'rank_partai', 'partai', 'pendidikan_clean', 'organisasi_clean'
        ]
        
        # Tambahkan kolom yang hilang dengan nilai default
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Pilih hanya kolom yang dibutuhkan
        df = df[required_columns]
        
        # Insert ke database
        df.to_sql('anggota_dpr', conn, if_exists='replace', index=False)
        
        conn.close()
        
        print(f"✅ Data berhasil diimport ke database SQLite!")
        print(f"   Total records: {len(df)}")
        return True
        
    except Exception as e:
        print(f"❌ Error saat import: {e}")
        return False

def verify_database():
    """Verifikasi database dan tampilkan statistik"""
    try:
        conn = sqlite3.connect('dpr_data.db')
        cursor = conn.cursor()
        
        # Hitung total records
        cursor.execute("SELECT COUNT(*) FROM anggota_dpr")
        total = cursor.fetchone()[0]
        
        # Sample data
        cursor.execute("SELECT nama, fraksi, partai FROM anggota_dpr LIMIT 5")
        samples = cursor.fetchall()
        
        # Statistik fraksi
        cursor.execute("SELECT fraksi, COUNT(*) as jumlah FROM anggota_dpr GROUP BY fraksi ORDER BY jumlah DESC LIMIT 5")
        fraksi_stats = cursor.fetchall()
        
        conn.close()
        
        print("\n" + "="*50)
        print("VERIFIKASI DATABASE")
        print("="*50)
        print(f"Total anggota DPR: {total}")
        print("\nSample data:")
        for i, (nama, fraksi, partai) in enumerate(samples, 1):
            print(f"{i}. {nama} - {fraksi} ({partai})")
        
        print("\nStatistik per fraksi:")
        for fraksi, jumlah in fraksi_stats:
            print(f"- {fraksi}: {jumlah} orang")
        
        print("="*50)
        
    except Exception as e:
        print(f"Error verifikasi: {e}")

if __name__ == "__main__":
    print("🚀 Setup Database SQLite untuk Portal DPR")
    print("-" * 40)
    
    # 1. Buat database dan tabel
    create_database()
    
    # 2. Import data dari CSV
    csv_files = ['dpr_data_clean.csv']
    
    imported = False
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            print(f"\nMenggunakan file: {csv_file}")
            if import_from_csv(csv_file):
                imported = True
                break
        else:
            print(f"File {csv_file} tidak ditemukan")
    
    if not imported:
        print("❌ Tidak ada file CSV yang berhasil diimport!")
        print("Pastikan file CSV ada di direktori yang sama dengan script ini.")
    else:
        # 3. Verifikasi hasil
        verify_database()