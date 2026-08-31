import { useState, useRef, useEffect, useCallback } from 'react'
import pavicLogo from '../assets/pavic_logo.jpg'
import { getUserHistory, saveHistoryItem } from '../utils/historyStorage'
import { imageApi } from '../services/imageApi'
import { authApi } from '../services/authApi'
import './Home.css'


// Converte DataURL Base64 em objeto File para envio ao backend se necessário
async function dataUrlToFile(dataUrl, fileName) {
  const res = await fetch(dataUrl)
  const blob = await res.blob()
  return new File([blob], fileName || 'imagem.png', { type: blob.type || 'image/png' })
}

export default function Home({
  currentUser,
  onLogout,
  onNavigateToHistory,
  pendingHistoryItem,
  onClearPendingHistoryItem,
}) {
  const [selectedAlgorithm, setSelectedAlgorithm] = useState(() => {
    const raw = String(pendingHistoryItem?.process || '').toLowerCase()
    const rawLabel = String(pendingHistoryItem?.processLabel || '').toLowerCase()
    if (raw.includes('super-resolution') || raw.includes('esc') || rawLabel.includes('super-resolution')) {
      return 'super-resolution'
    }
    return 'dehazing'
  })
  const [scaleFactor, setScaleFactor] = useState(() => {
    if (pendingHistoryItem?.scale) return Number(pendingHistoryItem.scale)
    const raw = String(pendingHistoryItem?.process || '') + ' ' + String(pendingHistoryItem?.processLabel || '')
    if (raw.includes('X3') || raw.includes('3x') || raw.includes('_3')) return 3
    if (raw.includes('X4') || raw.includes('4x') || raw.includes('_4')) return 4
    return 2
  })
  const [selectedFile, setSelectedFile] = useState(() =>
    pendingHistoryItem
      ? {
          name: pendingHistoryItem.fileName || 'imagem_historico.png',
          size:
            pendingHistoryItem.fileSizeInBytes ||
            pendingHistoryItem.fileSize ||
            '1.0 MB',
        }
      : null
  )
  const [originalImageUrl, setOriginalImageUrl] = useState(
    () => pendingHistoryItem?.inputImage || null
  )
  const [processedImageUrl, setProcessedImageUrl] = useState(null)
  const [processMeta, setProcessMeta] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [toastMessage, setToastMessage] = useState(() =>
    pendingHistoryItem
      ? `Imagem "${
          pendingHistoryItem.fileName || 'selecionada'
        }" carregada com algoritmo "${
          pendingHistoryItem.processLabel ||
          (pendingHistoryItem.process === 'super-resolution'
            ? 'Super-Resolução'
            : 'Image Dehazing')
        }" pré-selecionado!`
      : null
  )
  const [historyCount, setHistoryCount] = useState(() => {
    return getUserHistory(currentUser?.email).length
  })
  const [errorMessage, setErrorMessage] = useState('')

  const fileInputRef = useRef(null)

  // Atualiza a contagem de itens no histórico
  const refreshHistoryCount = useCallback(() => {
    const email = currentUser?.email || authApi.getCurrentUser()?.email
    if (email) {
      setHistoryCount(getUserHistory(email).length)
    }
  }, [currentUser])

  const currentUserRef = useRef(currentUser)
  useEffect(() => {
    currentUserRef.current = currentUser
  }, [currentUser])

  const selectedFileRef = useRef(selectedFile)
  useEffect(() => {
    selectedFileRef.current = selectedFile
  }, [selectedFile])

  // Processamento da imagem via IA no Backend (Depth Anything V2 + UDPNet / ESC) ou Canvas Fallback
  const executeProcessing = useCallback(
    async (inputSrc, algorithm, fileMeta = null) => {
      if (!inputSrc) return

      setIsProcessing(true)
      setProcessedImageUrl(null)
      setProcessMeta(null)

      const activeUser = currentUserRef.current || currentUser || authApi.getCurrentUser()
      const currentMeta = fileMeta || selectedFileRef.current
      const token = authApi.getToken()


      let resultDataUrl = null
      let imgWidth = 800
      let imgHeight = 600
      let createdImageId = null

      // 1. Tenta executar a inferência de IA no backend Django (Depth Anything V2 + UDPNet para Dehazing ou ESC para Super-Resolution)
      try {
        const endpoint =
          algorithm === 'dehazing'
            ? 'http://127.0.0.1:8000/api/processar/dehazing/'
            : 'http://127.0.0.1:8000/api/processar/super-resolution/'

        const headers = { 'Content-Type': 'application/json' }
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
        }

        const payload = {
          imagem_base64: inputSrc,
          nome_arquivo: currentMeta?.name || 'imagem_upload.png',
          algoritmo: algorithm,
          encoder: 'vits',
          grayscale: true,
          scale: 2,
        }

        const response = await fetch(endpoint, {
          method: 'POST',
          headers,
          body: JSON.stringify(payload),
        })

        if (response.ok) {
          const data = await response.json()
          if (data?.dados?.imagem_base64) {
            resultDataUrl = data.dados.imagem_base64
            imgWidth = data.dados.largura_processada || imgWidth
            imgHeight = data.dados.altura_processada || imgHeight
            createdImageId = data.dados.imagem_id || null
            setProcessMeta(data.dados)
          }
        }
      } catch (backendErr) {
        console.warn('Backend indisponível para IA no momento, utilizando processamento local:', backendErr.message)
      }

      // 2. Se a chamada ao backend não retornou imagem (ex: sem conexão), executa o fallback em Canvas
      if (!resultDataUrl) {
        resultDataUrl = await new Promise((resolve) => {
          const img = new Image()
          img.crossOrigin = 'Anonymous'
          img.src = inputSrc
          img.onload = () => {
            imgWidth = img.width
            imgHeight = img.height
            const canvas = document.createElement('canvas')
            const ctx = canvas.getContext('2d')
            canvas.width = img.width
            canvas.height = img.height
            ctx.drawImage(img, 0, 0)
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
            const data = imageData.data

            if (algorithm === 'dehazing') {
              for (let i = 0; i < data.length; i += 4) {
                let r = data[i]
                let g = data[i + 1]
                let b = data[i + 2]
                const minChannel = Math.min(r, g, b)
                const hazeEstimate = minChannel * 0.45
                r = Math.min(255, Math.max(0, (r - hazeEstimate) * 1.25))
                g = Math.min(255, Math.max(0, (g - hazeEstimate) * 1.25))
                b = Math.min(255, Math.max(0, (b - hazeEstimate) * 1.25))
                const avg = (r + g + b) / 3
                data[i] = Math.min(255, Math.max(0, avg + (r - avg) * 1.15))
                data[i + 1] = Math.min(255, Math.max(0, avg + (g - avg) * 1.15))
                data[i + 2] = Math.min(255, Math.max(0, avg + (b - avg) * 1.15))
              }
            } else {
              const width = canvas.width
              const height = canvas.height
              const copy = new Uint8ClampedArray(data)
              for (let y = 1; y < height - 1; y++) {
                for (let x = 1; x < width - 1; x++) {
                  const idx = (y * width + x) * 4
                  for (let c = 0; c < 3; c++) {
                    const top = ((y - 1) * width + x) * 4 + c
                    const bottom = ((y + 1) * width + x) * 4 + c
                    const left = (y * width + (x - 1)) * 4 + c
                    const right = (y * width + (x + 1)) * 4 + c
                    const val =
                      5 * copy[idx + c] -
                      copy[top] -
                      copy[bottom] -
                      copy[left] -
                      copy[right]
                    data[idx + c] = Math.min(255, Math.max(0, val))
                  }
                }
              }
            }
            ctx.putImageData(imageData, 0, 0)
            resolve(canvas.toDataURL('image/png'))
          }
          img.onerror = () => resolve(null)
        })
      }

      setProcessedImageUrl(resultDataUrl)
      setIsProcessing(false)

      // 3. Salva no histórico individual do usuário
      const activeEmail = activeUser?.email
      if (activeEmail && resultDataUrl) {
        const fileSizeFormatted = currentMeta?.size
          ? typeof currentMeta.size === 'number'
            ? `${(currentMeta.size / (1024 * 1024)).toFixed(2)} MB`
            : currentMeta.size
          : '1.0 MB'

        saveHistoryItem(activeEmail, {
          db_id: createdImageId,
          id: createdImageId ? `db_${createdImageId}` : undefined,
          skipApiSave: Boolean(createdImageId),
          inputImage: inputSrc,
          processedImage: resultDataUrl,
          process: algorithm,
          fileName: currentMeta?.name || 'imagem_processada.png',
          fileSize: fileSizeFormatted,
          fileSizeInBytes:
            typeof currentMeta?.size === 'number' ? currentMeta.size : 0,
          dimensions: `${imgWidth}x${imgHeight} px`,
        }).then(() => {
          refreshHistoryCount()
        })
      }
    },
    [refreshHistoryCount]
  )

  // Quando o componente recebe um item do histórico para reprocessamento
  useEffect(() => {
    if (pendingHistoryItem && pendingHistoryItem.inputImage) {
      const src = pendingHistoryItem.inputImage
      const rawProcess = String(pendingHistoryItem.process || '').toLowerCase()
      const rawLabel = String(pendingHistoryItem.processLabel || '').toLowerCase()
      const isSR =
        rawProcess.includes('super-resolution') ||
        rawProcess.includes('esc') ||
        rawLabel.includes('super-resolution')

      const algo = isSR ? 'super-resolution' : 'dehazing'

      let scale = 2
      if (pendingHistoryItem.scale) {
        scale = Number(pendingHistoryItem.scale)
      } else if (rawProcess.includes('x3') || rawLabel.includes('3x') || rawProcess.includes('_3')) {
        scale = 3
      } else if (rawProcess.includes('x4') || rawLabel.includes('4x') || rawProcess.includes('_4')) {
        scale = 4
      } else if (rawProcess.includes('x2') || rawLabel.includes('2x') || rawProcess.includes('_2')) {
        scale = 2
      }

      const meta = {
        name: pendingHistoryItem.fileName || 'imagem_historico.png',
        size:
          pendingHistoryItem.fileSizeInBytes ||
          pendingHistoryItem.fileSize ||
          '1.0 MB',
      }

      setSelectedAlgorithm(algo)
      setScaleFactor(scale)
      setSelectedFile(meta)
      setOriginalImageUrl(src)
      setProcessedImageUrl(null)
      setProcessMeta(null)
      setErrorMessage('')
      setToastMessage(
        `Imagem "${meta.name}" carregada com algoritmo "${isSR ? `Super-Resolução (${scale}x)` : 'Image Dehazing'}" pré-selecionado!`
      )

      if (onClearPendingHistoryItem) {
        onClearPendingHistoryItem()
      }
    }
  }, [pendingHistoryItem, onClearPendingHistoryItem])

  const handleFileChange = (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setErrorMessage('Por favor, selecione um arquivo de imagem válido (PNG, JPG, JPEG).')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('O tamanho do arquivo deve ser de até 10MB.')
      return
    }

    setErrorMessage('')
    setSelectedFile(file)

    const reader = new FileReader()
    reader.onload = (e) => {
      setOriginalImageUrl(e.target.result)
      setProcessedImageUrl(null)
      setProcessMeta(null)
    }
    reader.readAsDataURL(file)
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
    setProcessMeta(null)
    setErrorMessage('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Processamento da imagem (Super-Resolução ou Dehazing via API Backend)
  const handleProcessClick = async () => {
    if (!originalImageUrl || !selectedFile || isProcessing) return

    setIsProcessing(true)
    setErrorMessage('')
    setProcessedImageUrl(null)
    setProcessMeta(null)

    try {
      let fileToSend = selectedFile
      if (!(selectedFile instanceof File)) {
        fileToSend = await dataUrlToFile(originalImageUrl, selectedFile.name || 'imagem.png')
      }

      let resultado
      if (selectedAlgorithm === 'super-resolution') {
        resultado = await imageApi.processSuperResolution(fileToSend, scaleFactor)
      } else {
        resultado = await imageApi.processDehazing(fileToSend)
      }

      setProcessedImageUrl(resultado.dados.imagem_base64)
      setProcessMeta(resultado.dados)

      // Salva a imagem no histórico individual do usuário
      const activeEmail = currentUserRef.current?.email || currentUser?.email || authApi.getCurrentUser()?.email
      if (activeEmail) {
        const currentMeta = selectedFileRef.current
        const fileSizeFormatted = currentMeta?.size
          ? typeof currentMeta.size === 'number'
            ? `${(currentMeta.size / (1024 * 1024)).toFixed(2)} MB`
            : currentMeta.size
          : '1.0 MB'

        await saveHistoryItem(activeEmail, {
          db_id: resultado?.dados?.imagem_id,
          id: resultado?.dados?.imagem_id ? `db_${resultado.dados.imagem_id}` : undefined,
          skipApiSave: Boolean(resultado?.dados?.imagem_id),
          inputImage: originalImageUrl,
          processedImage: resultado.dados.imagem_base64,
          process: selectedAlgorithm,
          scale: selectedAlgorithm === 'super-resolution' ? scaleFactor : undefined,
          fileName: currentMeta?.name || (selectedAlgorithm === 'super-resolution' ? 'imagem_super_res.png' : 'imagem_dehazed.png'),
          fileSize: fileSizeFormatted,
          fileSizeInBytes: typeof currentMeta?.size === 'number' ? currentMeta.size : 0,
          dimensions: resultado.dados.resolucao_processada || 'N/A',
        })
        refreshHistoryCount()
      }
    } catch (error) {

      setErrorMessage(error.message || 'Erro ao processar imagem no backend.')
    } finally {
      setIsProcessing(false)
    }
  }



  const downloadProcessedImage = () => {
    if (!processedImageUrl) return
    const link = document.createElement('a')
    link.href = processedImageUrl
    const baseName = selectedFile?.name ? selectedFile.name.replace(/\.[^/.]+$/, '') : 'resultado'
    const scaleSuffix = selectedAlgorithm === 'super-resolution' ? `_x${scaleFactor}_ESC` : '_dehazed'
    link.download = `${baseName}${scaleSuffix}.png`
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
        <div className="header-right header-right-user">
          {/* User profile badge */}
          <div className="user-profile-badge">
            <div className="user-avatar-circle">
              {(currentUser?.nome || currentUser?.name || currentUser?.email || 'U')
                .charAt(0)
                .toUpperCase()}
            </div>
            <div className="user-info-text">
              <span className="header-tag">USUÁRIO</span>
              <span className="header-app-name">
                {currentUser?.nome || currentUser?.name || currentUser?.email || 'Usuário'}
              </span>
            </div>
          </div>

          <div className="header-action-group">
            {/* Histórico Button */}
            <button
              type="button"
              className="btn-history-nav"
              onClick={onNavigateToHistory}
              title="Acessar histórico de imagens"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 14 14" />
              </svg>
              <span>Histórico</span>
              {historyCount > 0 && (
                <span className="history-count-badge">{historyCount}</span>
              )}
            </button>

            {/* Logout Button */}
            <button
              type="button"
              className="btn-logout"
              onClick={onLogout}
              title="Sair da aplicação"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Sair
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Toast Alert Banner */}
        {toastMessage && (
          <div className="toast-banner success">
            <div className="toast-content">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              <span>{toastMessage}</span>
            </div>
            <button
              type="button"
              className="btn-close-toast"
              onClick={() => setToastMessage(null)}
              title="Fechar notificação"
            >
              ✕
            </button>
          </div>
        )}

        {/* Mensagem de Erro Global */}
        {errorMessage && (
          <div className="home-alert-error" role="alert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Hero Section */}
        <section className="hero-section">
          <div className="category-tag">
            <span className="category-line"></span>
            VISÃO COMPUTACIONAL & IA
          </div>
          <h1 className="hero-title">
            Aprimore suas imagens com <span className="highlight">redes neurais.</span>
          </h1>
          <p className="hero-subtitle">
            Escolha um algoritmo, selecione a escala e processe sua imagem utilizando modelos de Super-Resolução na GPU ou Image Dehazing com histórico sincronizado.
          </p>
        </section>

        {/* 1. Escolha o Algoritmo */}
        <section className="section">
          <h2 className="section-title">1. ESCOLHA O ALGORITMO</h2>
          <div className="algorithm-grid">
            {/* Card 1: Image Dehazing */}
            <div
              className={`algorithm-card ${selectedAlgorithm === 'dehazing' ? 'selected' : ''}`}
              onClick={() => {
                setSelectedAlgorithm('dehazing')
                setProcessedImageUrl(null)
                setProcessMeta(null)
              }}
            >
              {selectedAlgorithm === 'dehazing' && (
                <div className="card-dot"></div>
              )}
              <div className="card-icon-box dehazing">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M2 8c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                  <path d="M2 13c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                  <path d="M2 18c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                </svg>
              </div>
              <div className="card-content">
                <h3>Image Dehazing</h3>
                <p>
                  Remove névoa, neblina e haze atmosférico, restaurando cor e
                  contraste.
                </p>
              </div>
            </div>

            {/* Card 2: Super-Resolution */}
            <div
              className={`algorithm-card ${selectedAlgorithm === 'super-resolution' ? 'selected' : ''}`}
              onClick={() => {
                setSelectedAlgorithm('super-resolution')
                setProcessedImageUrl(null)
                setProcessMeta(null)
              }}
            >
              {selectedAlgorithm === 'super-resolution' && (
                <div className="card-dot"></div>
              )}
              <div className="card-icon-box super-resolution">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
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
                <p>Aumenta a resolução com rede neural profunda preservando nitidez e detalhes.</p>
              </div>
            </div>
          </div>

          {/* Seletor de Fator de Escala (Exibido quando Super-Resolution estiver ativo) */}
          {selectedAlgorithm === 'super-resolution' && (
            <div className="scale-selector-wrapper">
              <div className="scale-selector-title">
                <span className="label">Fator de Escala do Modelo</span>
                <span className="desc">Selecione o multiplicador de resolução para a reconstrução:</span>
              </div>
              <div className="scale-options-pills">
                <button
                  type="button"
                  className={`scale-pill-btn ${scaleFactor === 2 ? 'active' : ''}`}
                  onClick={() => {
                    setScaleFactor(2)
                    setProcessedImageUrl(null)
                    setProcessMeta(null)
                  }}
                  disabled={isProcessing}
                >
                  <span>X2</span>
                </button>
                <button
                  type="button"
                  className={`scale-pill-btn ${scaleFactor === 3 ? 'active' : ''}`}
                  onClick={() => {
                    setScaleFactor(3)
                    setProcessedImageUrl(null)
                    setProcessMeta(null)
                  }}
                  disabled={isProcessing}
                >
                  <span>X3</span>
                </button>
                <button
                  type="button"
                  className={`scale-pill-btn ${scaleFactor === 4 ? 'active' : ''}`}
                  onClick={() => {
                    setScaleFactor(4)
                    setProcessedImageUrl(null)
                    setProcessMeta(null)
                  }}
                  disabled={isProcessing}
                >
                  <span>X4</span>
                </button>
              </div>
            </div>
          )}
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
              onChange={(e) =>
                e.target.files && handleFileChange(e.target.files[0])
              }
            />
            <div className="upload-icon-circle">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div className="upload-title">
              Arraste sua imagem ou clique para enviar
            </div>
            <div className="upload-subtitle">PNG, JPG ou JPEG · até 10MB</div>

            {selectedFile && (
              <div className="file-info-badge">
                <span>
                  📁 {selectedFile.name}
                  {typeof selectedFile.size === 'number'
                    ? ` (${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)`
                    : selectedFile.size
                    ? ` (${selectedFile.size})`
                    : ''}
                </span>
                <button
                  type="button"
                  className="btn-remove-file"
                  onClick={removeFile}
                >
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
                  <img
                    src={originalImageUrl}
                    alt="Imagem original"
                    className="preview-image"
                  />
                ) : (
                  <div className="empty-placeholder">
                    <svg
                      width="48"
                      height="48"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
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
                {processedImageUrl && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="processed-badge">PROCESSADO</span>
                    {processMeta && (
                      <span className="process-meta-info" title={`Executado em ${processMeta.dispositivo}`}>
                        {processMeta.resolucao_processada} · {processMeta.tempo_execucao_segundos}s
                      </span>
                    )}
                  </div>
                )}
              </div>
              <div className="preview-body">
                {isProcessing ? (
                  <div className="empty-placeholder">
                    <div className="spinner" style={{ width: '32px', height: '32px', borderTopColor: '#F06529', borderWidth: '3px' }}></div>
                    <p style={{ marginTop: '12px', color: '#F06529', fontWeight: 600 }}>
                      {selectedAlgorithm === 'super-resolution'
                        ? `Processando Super-Resolução (${scaleFactor}x) na GPU...`
                        : 'Processando Dehazing...'}
                    </p>
                  </div>
                ) : processedImageUrl ? (
                  <img
                    src={processedImageUrl}
                    alt="Imagem processada"
                    className="preview-image"
                  />
                ) : (
                  <div className="empty-placeholder">
                    <svg
                      width="48"
                      height="48"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
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
              Algoritmo:{' '}
              <strong>
                {selectedAlgorithm === 'dehazing'
                  ? 'Image Dehazing'
                  : `Super-Resolution (${scaleFactor}x)`}
              </strong>
            </div>
            <div className="action-buttons">
              <button
                type="button"
                className={`btn-process ${
                  originalImageUrl ? 'active' : 'btn-disabled'
                } ${isProcessing ? 'processing' : ''}`}
                onClick={handleProcessClick}
                disabled={!originalImageUrl || isProcessing}
              >
                {isProcessing ? (
                  <>
                    <div className="spinner"></div> Processando...
                  </>
                ) : (
                  <>
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                    Processar imagem
                  </>
                )}
              </button>

              <button
                type="button"
                className={`btn-download ${
                  processedImageUrl ? 'ready' : 'btn-disabled'
                }`}
                onClick={downloadProcessedImage}
                disabled={!processedImageUrl}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
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
