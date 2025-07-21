# 3D Point Cloud Inference Application

## Proje Açıklaması

3D Point Cloud Inference Application, 3D nokta bulutları üzerinde segmentasyon, kalibrasyon ve nesne eşleştirme işlemleri gerçekleştiren PyQt5 tabanlı bir masaüstü uygulamasıdır. Uygulama, CAD dosyalarından dönüştürülen 3D nokta bulutları ile kamera verileri arasında karşılaştırma ve analiz yapabilme özelliği sunar.

## Ana Özellikler

### 🏠 Ana Sayfa (Home Page)
- **Screen 3D Point Cloud**: Kamera veya .ply dosyasından yüklenen 3D nokta bulutlarının görselleştirilmesi
- **CAD → Point Cloud**: STL dosyalarının nokta bulutuna dönüştürülmesi ve görüntülenmesi
- **Segmentasyon Point Cloud**: Segmentasyon sonuçlarının renkli görselleştirilmesi
- **Eşleştirme Point Cloud**: ICP tabanlı hizalama sonuçlarının karşılaştırmalı gösterimi

### 📈 Segmentasyon Sayfası
- **RANSAC Algoritması**: Düzlem segmentasyonu için RANSAC parametrelerinin ayarlanması
- **DBSCAN Kümeleme**: Nesne ayrıştırması için DBSCAN clustering
- **Threading Desteği**: Arka planda çalışan segmentasyon işlemleri
- **Parametre Yönetimi**: Distance threshold, iterasyon sayısı, eps ve min_points ayarları

### ⚙️ Kalibrasyon Sayfası
- Kamera kalibrasyonu ve ayarları

### 🔧 Ayarlar Sayfası
- Tema seçimi (Dark/Light)
- CAD dosyası nokta sayısı ayarları
- Konfigürasyon yönetimi

### 👤 Hesap Sayfası
- Kullanıcı hesap yönetimi

## Teknoloji Yığını

### Temel Kütüphaneler
- **PyQt5**: GUI framework
- **Open3D**: 3D nokta bulutu işleme
- **VisPy**: 3D görselleştirme
- **NumPy**: Numerik hesaplamalar
- **Matplotlib**: Renk paleti ve görselleştirme

### Desteklenen Formatlar
- **Input**: STL, PLY dosyaları
- **Output**: PLY nokta bulutları
- **Config**: JSON konfigürasyon dosyaları

## Proje Yapısı

```
3DInference/
├── run_app.py                 # Ana uygulama başlatıcı
├── gui/                       # GUI modülleri
│   ├── windows.py            # Ana pencere ve navigasyon
│   ├── style.py              # Tema ve stil yönetimi
│   ├── pages/                # Uygulama sayfaları
│   │   ├── home_page.py      # Ana sayfa - 4 panel görselleştirme
│   │   ├── segmentation_page.py  # Segmentasyon işlemleri
│   │   ├── calibration_page.py   # Kamera kalibrasyonu
│   │   ├── settings_page.py      # Uygulama ayarları
│   │   └── account_page.py       # Kullanıcı hesabı
│   ├── config/               # Konfigürasyon yönetimi
│   │   ├── config_util.py    # Genel ayarlar
│   │   └── segmentation_config.py  # Segmentasyon ayarları
│   ├── utils/                # Yardımcı modüller
│   │   └── viewer.py         # 3D görüntüleyici
│   └── icons/                # Tema ikonları
│       ├── dark/
│       └── light/
└── config/                   # Konfigürasyon dosyaları
    ├── settings.json         # Genel uygulama ayarları
    └── segmentations.json    # Segmentasyon parametreleri
```

## Kurulum

### Sistem Gereksinimleri
```bash
# Ubuntu/Debian için gerekli sistem kütüphaneleri
sudo apt-get update
sudo apt-get install python3 python3-pip
sudo apt-get install libgl1-mesa-glx libegl1-mesa libxrandr2 libxss1 libxcursor1 libxcomposite1 libasound2 libxi6 libxtst6
```

### Python Bağımlılıkları
```bash
# Temel kütüphaneler
pip install PyQt5
pip install open3d
pip install vispy
pip install numpy
pip install matplotlib

# İsteğe bağlı görselleştirme için
pip install opencv-python
```

## Kullanım

### Uygulamayı Başlatma
```bash
cd 3DInference
python run_app.py
```

### Temel İş Akışı

1. **Veri Yükleme**:
   - Ana sayfada "Offline" butonu ile .ply dosyası yükleyin
   - CAD listesinden STL dosyası seçin

2. **Segmentasyon**:
   - Segmentasyon sayfasına geçin
   - RANSAC parametrelerini ayarlayın
   - "Segmentasyon Başlat" butonuna tıklayın

3. **Eşleştirme**:
   - Ana sayfada "Eşleştir" butonu ile ICP hizalaması yapın
   - Fitness ve RMSE değerlerini kontrol edin

4. **Ayarlar**:
   - Tema değiştirme
   - CAD nokta sayısını ayarlama
   - Parametreleri kaydetme

## Algoritmalar

### RANSAC Plane Segmentation
```python
# Temel parametreler
distance_threshold: 0.01    # Düzlem mesafe toleransı
num_iterations: 1000        # RANSAC iterasyon sayısı
```

### DBSCAN Clustering
```python
# Kümeleme parametreleri
eps: 50.8                   # Komşuluk mesafesi
min_points: 500             # Minimum nokta sayısı
```

### ICP Registration
```python
# Hizalama parametreleri
voxel_size: 0.01 * diagonal  # Voxel boyutu
max_correspondence_distance: voxel  # Maksimum mesafe
max_iteration: 50            # Maksimum iterasyon
```

## Konfigürasyon

### settings.json
```json
{
  "theme": "dark",           // Tema: "dark" veya "light"
  "cad_point_count": 10000   // CAD dosyası nokta sayısı
}
```

### segmentations.json
```json
{
  "source_mode": "offline",
  "ply_file_path": "/path/to/file.ply",
  "algorithm": "RANSAC",
  "ransac_params": {
    "distance_threshold": 0.01,
    "num_iterations": 1000,
    "eps": 1.2,
    "min_points": 0.25
  }
}
```

## Performans Optimizasyonları

### Nokta Bulutu Önbelleği
- STL dosyaları otomatik olarak nokta bulutuna dönüştürülür
- `dataset/STLtoPoint/` dizininde önbelleğe alınır
- Format: `{filename}_{point_count}pts.ply`

### Threading
- Segmentasyon işlemleri arka planda çalışır
- UI donmaları önlenir
- İptal edilebilir işlemler

### Bellek Yönetimi
- Voxel downsampling ile nokta sayısı azaltılır
- Statistical outlier removal ile gürültü temizlenir

## Geliştirici Notları

### Yeni Sayfa Ekleme
1. `gui/pages/` dizininde yeni sayfa dosyası oluşturun
2. `gui/windows.py` dosyasında sayfayı kaydedin
3. Icon dosyalarını `gui/icons/` dizininde ekleyin

### Tema Sistemi
- `gui/style.py` dosyasında tema paletleri tanımlıdır
- Dark ve Light tema desteklenir
- İkonlar tema otomatik güncellenir

### Thread Güvenliği
- Qt sinyalleri ile thread-safe iletişim
- Worker thread'ler segmentasyon için kullanılır
- Uygulama kapanışında thread temizliği yapılır

## Troubleshooting

### Yaygın Hatalar

1. **OpenGL Hatası**:
```bash
export LIBGL_ALWAYS_SOFTWARE=1
```

2. **Qt Platform Hatası**:
```bash
export QT_QPA_PLATFORM=xcb
```

3. **Nokta Bulutu Yüklenmiyor**:
- Dosya yolunu kontrol edin
- Dosya formatını doğrulayın (.ply, .stl)
- Dosya izinlerini kontrol edin

4. **Segmentasyon Donuyor**:
- Parametre değerlerini düşürün
- Nokta sayısını azaltın
- Voxel downsampling uygulayın
