import { useState, useRef } from 'react'
import pavicLogo from './assets/pavic_logo.jpg'
import './App.css'

function App() {
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('dehazing') // 'dehazing' | 'super-resolution'
  const [selectedFile, setSelectedFile] = useState(null)
  const [originalImageUrl, setOriginalImageUrl] = useState(null)
  const [processedImageUrl, setProcessedImageUrl] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isDragging, setIsDragging] = useState(false)

  const fileInputRef = useRef(null)

  const handleFileChange = (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      alert('Por favor, selecione um arquivo de imagem válido (PNG, JPG, JPEG).')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('O tamanho do arquivo deve ser de até 10MB.')
      return
    }

    setSelectedFile(file)
    const url = URL.createObjectURL(file)
    setOriginalImageUrl(url)
    setProcessedImageUrl(null)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0])
    }
  }

  const removeFile = (e) => {
    e.stopPropagation()
    setSelectedFile(null)
    setOriginalImageUrl(null)
    setProcessedImageUrl(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Image Processing Handler using Canvas
  const processImage = () => {
    if (!originalImageUrl || isProcessing) return

    setIsProcessing(true)

    const img = new Image()
    img.crossOrigin = 'Anonymous'
    img.src = originalImageUrl

    img.onload = () => {
      setTimeout(() => {
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')

        canvas.width = img.width
        canvas.height = img.height

        ctx.drawImage(img, 0, 0)

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
        const data = imageData.data

        if (selectedAlgorithm === 'dehazing') {
          // Dehazing Filter: Enhance contrast, remove haze/fog layer, boost saturation
          for (let i = 0; i < data.length; i += 4) {
            let r = data[i]
            let g = data[i + 1]
            let b = data[i + 2]

            // Calculate lightness/haze level
            const minChannel = Math.min(r, g, b)
            const hazeEstimate = minChannel * 0.45

            // Remove haze and restore contrast
            r = Math.min(255, Math.max(0, (r - hazeEstimate) * 1.25))
            g = Math.min(255, Math.max(0, (g - hazeEstimate) * 1.25))
            b = Math.min(255, Math.max(0, (b - hazeEstimate) * 1.25))

            // Slight saturation boost for restored haze colors
            const avg = (r + g + b) / 3
            data[i] = Math.min(255, Math.max(0, avg + (r - avg) * 1.15))
            data[i + 1] = Math.min(255, Math.max(0, avg + (g - avg) * 1.15))
            data[i + 2] = Math.min(255, Math.max(0, avg + (b - avg) * 1.15))
          }
        } else {
          // Super-Resolution Filter: Unsharp mask / Detail enhancement filter
          const width = canvas.width
          const height = canvas.height
          const copy = new Uint8ClampedArray(data)

          // 3x3 Sharpen Kernel
          for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
              const idx = (y * width + x) * 4
              for (let c = 0; c < 3; c++) {
                const top = ((y - 1) * width + x) * 4 + c
                const bottom = ((y + 1) * width + x) * 4 + c
                const left = (y * width + (x - 1)) * 4 + c
                const right = (y * width + (x + 1)) * 4 + c

                const val = 5 * copy[idx + c] - copy[top] - copy[bottom] - copy[left] - copy[right]
                data[idx + c] = Math.min(255, Math.max(0, val))
              }
            }
          }
        }

        ctx.putImageData(imageData, 0, 0)
        setProcessedImageUrl(canvas.toDataURL('image/png'))
        setIsProcessing(false)
      }, 600)
    }
  }

  const downloadProcessedImage = () => {
    if (!processedImageUrl) return
    const link = document.createElement('a')
    link.href = processedImageUrl
    link.download = `${selectedAlgorithm}_resultado.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="logo-container">
          <img src={pavicLogo} className="pavic-logo-img" alt="PAVIC Lab Logo" />
        </div>
        <div className="header-right">
          <span className="header-tag">APLICAÇÃO</span>
          <span className="header-app-name">Dehazing & Super-Resolution</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Hero Section */}
        <section className="hero-section">
          <div className="category-tag">
            <span className="category-line"></span>
            VISÃO COMPUTACIONAL
          </div>
          <h1 className="hero-title">
            Aprimore suas imagens com <span className="highlight">um clique.</span>
          </h1>
          <p className="hero-subtitle">
            Escolha um algoritmo, envie sua imagem e faça o download do resultado. Todo o processamento ocorre a partir do seu dispositivo.
          </p>
        </section>

        {/* 1. Escolha o Algoritmo */}
        <section className="section">
          <h2 className="section-title">1. ESCOLHA O ALGORITMO</h2>
          <div className="algorithm-grid">
            {/* Card 1: Image Dehazing */}
            <div
              className={`algorithm-card ${selectedAlgorithm === 'dehazing' ? 'selected' : ''}`}
              onClick={() => setSelectedAlgorithm('dehazing')}
            >
              {selectedAlgorithm === 'dehazing' && <div className="card-dot"></div>}
              <div className="card-icon-box dehazing">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 8c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                  <path d="M2 13c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                  <path d="M2 18c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                </svg>
              </div>
              <div className="card-content">
                <h3>Image Dehazing</h3>
                <p>Remove névoa, neblina e haze atmosférico, restaurando cor e contraste.</p>
              </div>
            </div>

            {/* Card 2: Super-Resolution */}
            <div
              className={`algorithm-card ${selectedAlgorithm === 'super-resolution' ? 'selected' : ''}`}
              onClick={() => setSelectedAlgorithm('super-resolution')}
            >
              {selectedAlgorithm === 'super-resolution' && <div className="card-dot"></div>}
              <div className="card-icon-box super-resolution">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  <polyline points="7.5 4.21 12 6.81 16.5 4.21" />
                  <polyline points="7.5 19.79 7.5 14.6 3 12" />
                  <polyline points="21 12 16.5 14.6 16.5 19.79" />
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                  <line x1="12" y1="22.08" x2="12" y2="12" />
                </svg>
              </div>
              <div className="card-content">
                <h3>Super-Resolution</h3>
                <p>Aumenta a resolução da imagem preservando detalhes e nitidez.</p>
              </div>
            </div>
          </div>
        </section>

        {/* 2. Envie a Imagem */}
        <section className="section">
          <h2 className="section-title">2. ENVIE A IMAGEM</h2>
          <div
            className={`upload-zone ${isDragging ? 'dragging' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept="image/png, image/jpeg, image/jpg"
              onChange={(e) => e.target.files && handleFileChange(e.target.files[0])}
            />
            <div className="upload-icon-circle">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div className="upload-title">Arraste sua imagem ou clique para enviar</div>
            <div className="upload-subtitle">PNG, JPG ou JPEG · até 10MB</div>

            {selectedFile && (
              <div className="file-info-badge">
                <span>📁 {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)</span>
                <button type="button" className="btn-remove-file" onClick={removeFile}>
                  Remover
                </button>
              </div>
            )}
          </div>
        </section>

        {/* 3. Processar e Visualizar */}
        <section className="section">
          <h2 className="section-title">3. PROCESSAR E VISUALIZAR</h2>
          <div className="preview-grid">
            {/* Panel Original */}
            <div className="preview-card">
              <div className="preview-header">
                <span className="preview-header-title">ORIGINAL</span>
              </div>
              <div className="preview-body">
                {originalImageUrl ? (
                  <img src={originalImageUrl} alt="Imagem original" className="preview-image" />
                ) : (
                  <div className="empty-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <p>Sem imagem</p>
                  </div>
                )}
              </div>
            </div>

            {/* Panel Resultado */}
            <div className="preview-card">
              <div className="preview-header">
                <span className="preview-header-title">RESULTADO</span>
                {processedImageUrl && <span className="processed-badge">PROCESSADO</span>}
              </div>
              <div className="preview-body">
                {isProcessing ? (
                  <div className="empty-placeholder">
                    <div className="spinner" style={{ width: '28px', height: '28px', borderTopColor: '#F06529' }}></div>
                    <p style={{ marginTop: '12px', color: '#F06529', fontWeight: 600 }}>Processando imagem...</p>
                  </div>
                ) : processedImageUrl ? (
                  <img src={processedImageUrl} alt="Imagem processada" className="preview-image" />
                ) : (
                  <div className="empty-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <p>Sem imagem</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bottom Control Bar */}
          <div className="actions-bar">
            <div className="selected-algo-info">
              Algoritmo selecionado: <strong>{selectedAlgorithm === 'dehazing' ? 'Image Dehazing' : 'Super-Resolution'}</strong>
            </div>
            <div className="action-buttons">
              <button
                type="button"
                className={`btn-process ${originalImageUrl ? 'active' : 'btn-disabled'} ${isProcessing ? 'processing' : ''}`}
                onClick={processImage}
                disabled={!originalImageUrl || isProcessing}
              >
                {isProcessing ? (
                  <>
                    <div className="spinner"></div> Processando...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                    Processar imagem
                  </>
                )}
              </button>

              <button
                type="button"
                className={`btn-download ${processedImageUrl ? 'ready' : 'btn-disabled'}`}
                onClick={downloadProcessedImage}
                disabled={!processedImageUrl}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        PAVIC Lab - Pesquisa Aplicada em Visão e Inteligência Computacional
      </footer>
    </div>
  )
}

export default App
