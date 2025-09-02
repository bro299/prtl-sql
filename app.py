# app_sqlite_render.py - Version khusus untuk Render
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
        """Pencarian dengan SQLite - optimized untuk Render"""
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
            
            return [dict(row) for row in results]
            
        except Exception as e:
            print(f"Search error: {e}")
            conn.close()
            return []

# Initialize search engine
dpr_search = DPRSQLiteSearch()

@app.route('/')
def index():
    """Halaman utama dengan HTML built-in untuk Render"""
    return '''
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🏛️ Portal Data DPR RI</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
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
            }
            .result-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
            }
            .loading {
                display: none;
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

            <!-- Loading -->
            <div id="loading" class="loading text-center mb-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Mencari...</span>
                </div>
                <div class="mt-2">Sedang mencari data...</div>
            </div>

            <!-- Results Section -->
            <div id="results"></div>

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

        <script>
            function searchMembers() {
                const query = document.getElementById('searchBox').value;
                const resultsDiv = document.getElementById('results');
                const loadingDiv = document.getElementById('loading');
                
                if (!query.trim()) {
                    resultsDiv.innerHTML = '<div class="alert alert-warning"><i class="fas fa-exclamation-triangle"></i> Masukkan kata kunci pencarian</div>';
                    return;
                }
                
                // Show loading
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
                                <div class="card result-card h-100">
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