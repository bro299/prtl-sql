# app_sqlite.py - Versi lengkap dengan tambahan tombol download dan FAQ

from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import re
from datetime import datetime

app = Flask(__name__)

class DPRSQLiteSearch:
    def __init__(self, db_path='dpr_data.db'):
        self.db_path = db_path
        self.check_database()
    
    def check_database(self):
        """Cek apakah database ada dan valid"""
        if not os.path.exists(self.db_path):
            print(f"❌ Database {self.db_path} tidak ditemukan!")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM anggota_dpr")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"✅ Database siap dengan {count} records")
            return True
        except Exception as e:
            print(f"❌ Error mengakses database: {e}")
            return False
    
    def get_db_connection(self):
        """Buat koneksi database dengan row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def search_by_name(self, query, limit=25):
        """Pencarian dengan SQLite - optimized untuk Render, memuat semua field seperti app.py"""
        if not query or not query.strip():
            return []
        
        query = query.strip()
        search_pattern = f"%{query}%"
        
        conn = self.get_db_connection()
        
        sql_query = """
        SELECT * FROM anggota_dpr 
        WHERE LOWER(nama) LIKE LOWER(?) 
           OR LOWER(fraksi) LIKE LOWER(?) 
           OR LOWER(partai) LIKE LOWER(?)
           OR LOWER(dapil) LIKE LOWER(?)
        ORDER BY 
            CASE 
                WHEN LOWER(nama) LIKE LOWER(?) THEN 1
                WHEN LOWER(fraksi) LIKE LOWER(?) THEN 2
                ELSE 3
            END,
            nama
        LIMIT ?
        """
        
        try:
            cursor = conn.execute(sql_query, [
                search_pattern, search_pattern, search_pattern, search_pattern,
                search_pattern, search_pattern, limit
            ])
            
            results = cursor.fetchall()
            conn.close()
            
            # Clean records mirip dengan app.py
            cleaned_results = [self.clean_member_record(dict(row)) for row in results]
            
            return cleaned_results
            
        except Exception as e:
            print(f"Search error: {e}")
            conn.close()
            return []

    def clean_member_record(self, record):
        """Clean up a member record for display, mirip dengan fungsi di app.py"""
        
        # Clean up organization field
        if 'organisasi' in record and record['organisasi']:
            record['organisasi_clean'] = self.extract_organizations(record['organisasi'])
        else:
            record['organisasi_clean'] = 'Tidak tersedia'
        
        # Ensure kota_lahir is available
        if 'kota_lahir' not in record or not record['kota_lahir']:
            if 'ttl' in record:
                record['kota_lahir'] = self.extract_birth_city(record['ttl'])
            else:
                record['kota_lahir'] = 'Tidak tersedia'
        
        # Ensure usia is calculated
        if 'usia' not in record or not record['usia']:
            if 'ttl' in record:
                record['usia'] = self.calculate_age(record['ttl'])
        
        # Clean AKD field (remove brackets and quotes)
        if 'akd_clean' in record and record['akd_clean']:
            akd = str(record['akd_clean'])
            akd = re.sub(r'[\[\]\'""]', '', akd)
            akd = akd.replace(',', ', ')
            record['akd_clean'] = akd
        
        # Ensure required fields have default values
        required_fields = {
            'nama': 'Nama tidak tersedia',
            'fraksi': 'Fraksi tidak tersedia',
            'dapil': 'Dapil tidak tersedia',
            'akd_clean': 'Tidak tersedia',
            'ttl': 'Tidak tersedia',
            'agama': 'Tidak tersedia',
            'kota_lahir': 'Tidak tersedia',
            'usia_kategori': 'Tidak tersedia',
            'is_kader': '0',
            'is_dewan': '0',
            'pendidikan': 'Tidak tersedia',
            'pekerjaan': 'Tidak tersedia',
            'organisasi': 'Tidak tersedia',
            'pendidikan_clean': 'Tidak tersedia',
            'organisasi_clean': 'Tidak tersedia'
        }
        
        for field, default in required_fields.items():
            if field not in record or not record[field]:
                record[field] = default
        
        return record

    def extract_education(self, edu_text):
        """Extract clean education info from long text, dari app.py"""
        if not edu_text or edu_text.strip() == '':
            return 'Tidak tersedia'
        
        # Look for highest education level mentioned
        edu_levels = ['S3', 'S2', 'S1', 'DIPLOMA', 'SMA', 'SMP', 'SD']
        edu_text_upper = str(edu_text).upper()
        
        for level in edu_levels:
            if level in edu_text_upper:
                # Try to extract institution name after the level
                pattern = rf'{level}[,\s]*([^.]+)'
                match = re.search(pattern, edu_text_upper)
                if match:
                    institution = match.group(1).strip()
                    return f"{level} - {institution}"
                return level
        
        return str(edu_text)[:100] + '...' if len(str(edu_text)) > 100 else str(edu_text)
    
    def extract_organizations(self, org_text):
        """Extract clean organization info, dari app.py"""
        if not org_text or org_text.strip() == '':
            return 'Tidak tersedia'
        
        # Split by common separators and take first few organizations
        orgs = re.split(r'[,\d]+\.', str(org_text))
        clean_orgs = []
        
        for org in orgs[:3]:  # Take first 3 organizations
            org = org.strip()
            if org and len(org) > 5:  # Filter out very short/meaningless entries
                # Remove "Sebagai:" and year info
                org = re.sub(r'Sebagai:.*?Tahun:.*?\d{4}.*?-.*?\d{0,4}', '', org)
                org = org.strip()
                if org:
                    clean_orgs.append(org)
        
        return ', '.join(clean_orgs) if clean_orgs else str(org_text)[:100]
    
    def extract_birth_city(self, ttl):
        """Extract birth city from TTL field, dari app.py"""
        if not ttl or ttl.strip() == '':
            return 'Tidak tersedia'
        
        # TTL format is usually "City / Date"
        if '/' in str(ttl):
            city = str(ttl).split('/')[0].strip()
            return city if city else 'Tidak tersedia'
        
        return str(ttl)
    
    def calculate_age(self, ttl):
        """Calculate age from TTL field, dari app.py"""
        if not ttl or ttl.strip() == '':
            return None
        
        try:
            # Extract date part after "/"
            if '/' in str(ttl):
                date_part = str(ttl).split('/')[-1].strip()
                
                # Try to parse various date formats
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

# Initialize search engine
dpr_search = DPRSQLiteSearch()

@app.route('/')
def index():
    """Halaman utama dengan HTML built-in untuk Render, tambahan tombol download dan FAQ"""
    return '''
    <!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    
    <!-- Basic SEO Meta Tags -->
    <title>🏛️ Portal Data DPR RI - Informasi Anggota dan Data Parlemen Indonesia</title>
    <meta name="description" content="Portal resmi data DPR RI yang menyediakan informasi lengkap tentang anggota parlemen, fraksi, komisi, dan kegiatan legislatif Dewan Perwakilan Rakyat Republik Indonesia.">
    <meta name="keywords" content="DPR RI, anggota DPR, parlemen Indonesia, data legislatif, fraksi DPR, komisi DPR, Dewan Perwakilan Rakyat">
    <meta name="author" content="DPR RI">
    <meta name="robots" content="index, follow">
    <meta name="language" content="Indonesian">
    
    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://www.dpr.go.id/">
    <meta property="og:title" content="🏛️ Portal Data DPR RI - Informasi Anggota dan Data Parlemen Indonesia">
    <meta property="og:description" content="Portal resmi data DPR RI yang menyediakan informasi lengkap tentang anggota parlemen, fraksi, komisi, dan kegiatan legislatif Dewan Perwakilan Rakyat Republik Indonesia.">
    <meta property="og:image" content="https://www.dpr.go.id/images/dpr-logo.png">
    <meta property="og:locale" content="id_ID">
    <meta property="og:site_name" content="Portal Data DPR RI">
    
    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="https://www.dpr.go.id/">
    <meta property="twitter:title" content="🏛️ Portal Data DPR RI - Informasi Anggota dan Data Parlemen Indonesia">
    <meta property="twitter:description" content="Portal resmi data DPR RI yang menyediakan informasi lengkap tentang anggota parlemen, fraksi, komisi, dan kegiatan legislatif Dewan Perwakilan Rakyat Republik Indonesia.">
    <meta property="twitter:image" content="https://www.dpr.go.id/images/dpr-logo.png">
    
    <!-- Additional SEO Meta Tags -->
    <meta name="theme-color" content="#1e40af">
    <meta name="msapplication-TileColor" content="#1e40af">
    <meta name="application-name" content="Portal Data DPR RI">
    <meta name="apple-mobile-web-app-title" content="Portal Data DPR RI">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    
    <!-- Canonical URL -->
    <link rel="canonical" href="https://www.dpr.go.id/">
    <meta name="google-site-verification" content="JtgNVwnmHRdM1FfwcKIEXv1EJ8DuTu5kYqyFcpoAo_c" />
    
        <style>
            .hero-section {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 3rem 0;
                margin-bottom: 2rem;
            }
            .search-card {
                border: none;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-radius: 15px;
            }
            .result-card {
                transition: transform 0.2s;
                border-radius: 10px;
                cursor: pointer;
            }
            .result-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
            }
            .loading {
                display: none;
            }
            .faq-section {
                margin-top: 3rem;
                background-color: #f8f9fa;
                padding: 2rem;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <!-- Hero Section -->
        <div class="hero-section">
            <div class="container text-center">
                <h1 class="display-4 mb-3">
                    <i class="fas fa-university"></i> Portal Data DPR RI
                </h1>
                <p class="lead">Pencarian Cepat Anggota DPR dengan Database SQLite</p>
                <div class="badge bg-success fs-6">✅ 500+ Records • ⚡ Super Fast Search</div>
            </div>
        </div>

        <div class="container">
            <!-- Search Section -->
            <div class="row justify-content-center mb-4">
                <div class="col-lg-8">
                    <div class="card search-card">
                        <div class="card-body p-4">
                            <h5 class="card-title mb-3">
                                <i class="fas fa-search text-primary"></i> Pencarian Anggota DPR
                            </h5>
                            
                            <div class="row g-3">
                                <div class="col-md-8">
                                    <input type="text" id="searchBox" class="form-control form-control-lg" 
                                           placeholder="Cari nama, fraksi, partai, atau daerah pemilihan..."
                                           autocomplete="off">
                                </div>
                                <div class="col-md-4">
                                    <button class="btn btn-primary btn-lg w-100" onclick="searchMembers()">
                                        <i class="fas fa-search me-2"></i>Cari
                                    </button>
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <small class="text-muted">
                                    <i class="fas fa-lightbulb"></i>
                                    Tip: Coba cari "PDIP", "Jokowi", nama daerah, atau nama anggota
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Download Button -->
            <div class="row justify-content-center mb-4">
                <div class="col-lg-8 text-center">
                    <a href="https://biteblob.com/Information/kUxw1tKiJi22gS/#dpr_data_clean.csv" class="btn btn-success btn-lg">
                        <i class="fas fa-download me-2"></i> Download Data DPR (CSV)
                    </a>
                </div>
            </div>

            <!-- Loading -->
            <div id="loading" class="loading text-center mb-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Mencari...</span>
                </div>
                <div class="mt-2">Sedang mencari data...</div>
            </div>

            <!-- Results Section -->
            <div id="results"></div>

            <!-- FAQ Section -->
            <div class="faq-section">
                <h3 class="mb-4">Mengapa Portal Ini Dibuat?</h3>
                <div class="accordion" id="faqAccordion">
                    <div class="accordion-item">
                        <h2 class="accordion-header" id="faq1">
                            <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne" aria-expanded="true" aria-controls="collapseOne">
                                Apa tujuan portal ini?
                            </button>
                        </h2>
                        <div id="collapseOne" class="accordion-collapse collapse show" aria-labelledby="faq1" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Portal ini dibuat sebagai bentuk partisipasi publik atas keresahan masyarakat terhadap kinerja DPR RI, khususnya menyusul aksi demonstrasi besar-besaran pada tahun 2025. Kami ingin meningkatkan transparansi dan akuntabilitas dengan menyediakan akses mudah ke data anggota DPR.
                            </div>
                        </div>
                    </div>
                    <div class="accordion-item">
                        <h2 class="accordion-header" id="faq2">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseTwo" aria-expanded="false" aria-controls="collapseTwo">
                                Mengapa transparansi penting?
                            </button>
                        </h2>
                        <div id="collapseTwo" class="accordion-collapse collapse" aria-labelledby="faq2" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Masyarakat menuntut keterbukaan informasi tentang kinerja, kehadiran, dan aktivitas anggota DPR yang selama ini kurang transparan. Portal ini memberikan data lengkap untuk memungkinkan kontrol publik.
                            </div>
                        </div>
                    </div>
                    <div class="accordion-item">
                        <h2 class="accordion-header" id="faq3">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseThree" aria-expanded="false" aria-controls="collapseThree">
                                Bagaimana data ini membantu?
                            </button>
                        </h2>
                        <div id="collapseThree" class="accordion-collapse collapse" aria-labelledby="faq3" data-bs-parent="#faqAccordion">
                            <div class="accordion-body">
                                Dengan menyediakan informasi seperti pendidikan, pekerjaan, dan organisasi anggota DPR, masyarakat dapat mengevaluasi kualitas dan komitmen wakil rakyat mereka, sekaligus mendorong akuntabilitas yang lebih besar.
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Info Section -->
            <div class="row mt-5">
                <div class="col-md-4">
                    <div class="card border-primary">
                        <div class="card-body text-center">
                            <i class="fas fa-database fa-2x text-primary mb-2"></i>
                            <h6>Database SQLite</h6>
                            <small>Pencarian super cepat dengan index</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card border-success">
                        <div class="card-body text-center">
                            <i class="fas fa-users fa-2x text-success mb-2"></i>
                            <h6>500+ Anggota DPR</h6>
                            <small>Data lengkap dan akurat</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card border-info">
                        <div class="card-body text-center">
                            <i class="fas fa-bolt fa-2x text-info mb-2"></i>
                            <h6>Response < 100ms</h6>
                            <small>Optimized untuk performa tinggi</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <footer class="bg-dark text-white text-center py-4 mt-5">
            <div class="container">
                <p class="mb-2">&copy; 2025 Portal Data DPR RI</p>
                <p class="mb-0">
                    <small>
                        Powered by Flask + SQLite • Hosted on Render
                        <a href="/debug" class="text-white ms-2">Debug Info</a> |
                        <a href="/stats" class="text-white ms-2">Statistik</a>
                    </small>
                </p>
            </div>
        </footer>

        <!-- Modal untuk Detail -->
        <div class="modal fade" id="memberModal" tabindex="-1" aria-labelledby="memberModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="memberModalLabel">Detail Anggota DPR</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div id="modalContent"></div>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/js/bootstrap.bundle.min.js"></script>
        <script>
            function searchMembers() {
                const query = document.getElementById('searchBox').value.trim();
                const resultsDiv = document.getElementById('results');
                const loadingDiv = document.getElementById('loading');

                if (!query) {
                    resultsDiv.innerHTML = '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle"></i> Masukkan kata kunci pencarian</div>';
                    return;
                }

                loadingDiv.style.display = 'block';
                resultsDiv.innerHTML = '';

                fetch('/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({query: query})
                })
                .then(response => response.json())
                .then(data => {
                    loadingDiv.style.display = 'none';
                    
                    if (data.error) {
                        resultsDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle"></i> ${data.error}</div>`;
                        return;
                    }
                    
                    if (data.results.length === 0) {
                        resultsDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-info-circle"></i> Tidak ada hasil ditemukan. Coba kata kunci lain.</div>';
                        return;
                    }
                    
                    let html = `
                        <div class="alert alert-success">
                            <i class="fas fa-check-circle"></i> 
                            Ditemukan <strong>${data.count}</strong> hasil untuk pencarian: "<strong>${data.query}</strong>"
                        </div>
                        <div class="row">
                    `;
                    
                    data.results.forEach(member => {
                        html += `
                            <div class="col-lg-4 col-md-6 mb-4">
                                <div class="card result-card h-100" onclick='showDetail(${JSON.stringify(member)})'>
                                    <div class="card-body">
                                        <h6 class="card-title text-primary">
                                            <i class="fas fa-user"></i> ${member.nama || 'Nama tidak tersedia'}
                                        </h6>
                                        <hr>
                                        <p class="card-text">
                                            <small class="text-muted">
                                                <i class="fas fa-flag"></i> <strong>Fraksi:</strong> ${member.fraksi || 'N/A'}<br>
                                                <i class="fas fa-building"></i> <strong>Partai:</strong> ${member.partai || 'N/A'}<br>
                                                <i class="fas fa-map-marker-alt"></i> <strong>Dapil:</strong> ${member.dapil || 'N/A'}<br>
                                                <i class="fas fa-birthday-cake"></i> <strong>Kota Lahir:</strong> ${member.kota_lahir || 'N/A'}
                                                ${member.usia ? `<br><i class="fas fa-calendar"></i> <strong>Usia:</strong> ${member.usia} tahun` : ''}
                                                ${member.agama ? `<br><i class="fas fa-pray"></i> <strong>Agama:</strong> ${member.agama}` : ''}
                                            </small>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                    resultsDiv.innerHTML = html;
                })
                .catch(error => {
                    loadingDiv.style.display = 'none';
                    resultsDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> Error: ${error.message}</div>`;
                });
            }

            function showDetail(member) {
                const modalContent = document.getElementById('modalContent');
                modalContent.innerHTML = `
                    <p><strong>Nama:</strong> ${member.nama}</p>
                    <p><strong>Fraksi:</strong> ${member.fraksi}</p>
                    <p><strong>Partai:</strong> ${member.partai}</p>
                    <p><strong>Dapil:</strong> ${member.dapil}</p>
                    <p><strong>AKD Clean:</strong> ${member.akd_clean}</p>
                    <p><strong>TTL:</strong> ${member.ttl}</p>
                    <p><strong>Agama:</strong> ${member.agama}</p>
                    <p><strong>Pendidikan:</strong> ${member.pendidikan}</p>
                    <p><strong>Pekerjaan:</strong> ${member.pekerjaan}</p>
                    <p><strong>Organisasi:</strong> ${member.organisasi}</p>
                    <p><strong>Kota Lahir:</strong> ${member.kota_lahir}</p>
                    <p><strong>Usia:</strong> ${member.usia ? member.usia : 'Tidak tersedia'}</p>
                    <p><strong>Pendidikan Terakhir:</strong> ${member.pendidikan_terakhir}</p>
                    <p><strong>Is Kader:</strong> ${member.is_kader}</p>
                    <p><strong>Is Dewan:</strong> ${member.is_dewan}</p>
                    <p><strong>Usia Kategori:</strong> ${member.usia_kategori}</p>
                    <p><strong>Rank Partai:</strong> ${member.rank_partai ? member.rank_partai : 'Tidak tersedia'}</p>
                    ${member.link_profil ? `<p><strong>Link Profil:</strong> <a href="${member.link_profil}" target="_blank">Lihat Profil</a></p>` : ''}
                    ${member.link_foto ? `<p><strong>Foto:</strong> <img src="${member.link_foto}" alt="Foto Anggota" style="max-width: 200px;"></p>` : ''}
                `;

                const modal = new bootstrap.Modal(document.getElementById('memberModal'));
                modal.show();
            }
            
            // Search on Enter key
            document.getElementById('searchBox').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchMembers();
                }
            });
            
            // Auto-focus search box
            document.getElementById('searchBox').focus();
        </script>
    </body>
    </html>
    '''

@app.route('/search', methods=['POST'])
def search():
    """Handle search requests"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Silakan masukkan kata kunci pencarian'})
        
        results = dpr_search.search_by_name(query)
        
        return jsonify({
            'results': results,
            'count': len(results),
            'query': query,
            'success': True
        })
    
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'})

@app.route('/download')
def download():
    """Provide download link for CSV data"""
    csv_path = 'dpr_data_clean.csv'
    if os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True)
    else:
        return jsonify({'error': 'File data tidak tersedia'}), 404

@app.route('/health')
def health_check():
    """Health check untuk Render"""
    try:
        conn = dpr_search.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM anggota_dpr")
        count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'records': count,
            'version': 'render-optimized'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/debug')
def debug_info():
    """Debug info"""
    try:
        conn = dpr_search.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT nama, fraksi, partai FROM anggota_dpr LIMIT 3")
        sample_data = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM anggota_dpr")
        total_rows = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'OK',
            'platform': 'Render',
            'database_path': dpr_search.db_path,
            'database_exists': os.path.exists(dpr_search.db_path),
            'total_rows': total_rows,
            'sample_data': sample_data,
            'environment': dict(os.environ)
        })
        
    except Exception as e:
        return jsonify({'error': f'Debug error: {str(e)}'}), 500

@app.route('/stats')
def get_stats():
    """Statistik data"""
    try:
        conn = dpr_search.get_db_connection()
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute("SELECT COUNT(*) FROM anggota_dpr")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT fraksi, COUNT(*) FROM anggota_dpr GROUP BY fraksi ORDER BY COUNT(*) DESC LIMIT 10")
        fraksi_stats = cursor.fetchall()
        
        cursor.execute("SELECT partai, COUNT(*) FROM anggota_dpr GROUP BY partai ORDER BY COUNT(*) DESC LIMIT 10")
        partai_stats = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'total_members': total,
            'top_fraksi': [{'name': row[0], 'count': row[1]} for row in fraksi_stats],
            'top_partai': [{'name': row[0], 'count': row[1]} for row in partai_stats],
            'platform': 'Render + SQLite'
        })
        
    except Exception as e:
        return jsonify({'error': f'Stats error: {str(e)}'}), 500

if __name__ == '__main__':
    # Render-specific configuration
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 Starting DPR Portal - Render Version")
    print(f"🌐 Port: {port}")
    print(f"💾 Database: {dpr_search.db_path}")
    print(f"📊 Environment: {os.environ.get('RENDER_SERVICE_NAME', 'local')}")
    
    # Production settings untuk Render
    app.run(host='0.0.0.0', port=port, debug=False)



