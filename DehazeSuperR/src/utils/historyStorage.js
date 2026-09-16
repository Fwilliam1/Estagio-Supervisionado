// Gerenciamento de Usuários e Histórico com Integração REST API (Django) e Fallback LocalStorage

const API_BASE_URL = 'http://127.0.0.1:8000/api'
const USERS_KEY = 'dsr_registered_users'
const CURRENT_USER_KEY = 'dsr_current_session_user'
const HISTORY_PREFIX = 'dsr_image_history_'

// Usuário padrão inicial
export const DEFAULT_USER = {
  id: '1',
  name: 'Administrador',
  email: 'admin@dsr.com',
}

/**
 * Obtém a lista de todos os usuários cadastrados localmente
 */
export function getRegisteredUsers() {
  try {
    const raw = localStorage.getItem(USERS_KEY)
    if (!raw) {
      const initialUsers = [DEFAULT_USER]
      localStorage.setItem(USERS_KEY, JSON.stringify(initialUsers))
      return initialUsers
    }
    return JSON.parse(raw)
  } catch {
    return [DEFAULT_USER]
  }
}

/**
 * Cadastra ou atualiza um usuário localmente
 */
export function registerUser(user) {
  const users = getRegisteredUsers()
  const existingIndex = users.findIndex(
    (u) => u.email.toLowerCase() === user.email.toLowerCase()
  )

  const newUser = {
    id: user.id || Date.now().toString(),
    name: user.name || user.email.split('@')[0],
    email: user.email.toLowerCase(),
  }

  if (existingIndex >= 0) {
    users[existingIndex] = { ...users[existingIndex], ...newUser }
  } else {
    users.push(newUser)
  }

  localStorage.setItem(USERS_KEY, JSON.stringify(users))
  return newUser
}

/**
 * Obtém o usuário atualmente logado
 */
export function getCurrentUser() {
  try {
    const raw = localStorage.getItem(CURRENT_USER_KEY)
    if (raw) {
      return JSON.parse(raw)
    }
  } catch (e) {
    console.error('Erro ao ler usuário atual:', e)
  }
  return DEFAULT_USER
}

/**
 * Define o usuário atualmente logado
 */
export function setCurrentUser(user) {
  if (!user) {
    localStorage.removeItem(CURRENT_USER_KEY)
    return
  }
  const normalizedUser = {
    id: user.id || Date.now().toString(),
    name: user.name || user.email.split('@')[0],
    email: (user.email || 'usuario@dsr.com').toLowerCase(),
  }
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(normalizedUser))
  registerUser(normalizedUser)
  return normalizedUser
}

/**
 * Remove a sessão do usuário atual
 */
export function clearCurrentUser() {
  localStorage.removeItem(CURRENT_USER_KEY)
}

/**
 * Retorna o histórico de imagens armazenado no LocalStorage (síncrono)
 */
export function getUserHistory(userEmail) {
  if (!userEmail) return []
  try {
    const key = `${HISTORY_PREFIX}${userEmail.toLowerCase()}`
    const raw = localStorage.getItem(key)
    if (!raw) return []
    return JSON.parse(raw)
  } catch (e) {
    console.error('Erro ao buscar histórico do usuário:', e)
    return []
  }
}

/**
 * Sincroniza e busca o histórico diretamente da REST API do Django
 */
export async function fetchUserHistoryFromApi(userEmail) {
  if (!userEmail) return []
  try {
    const response = await fetch(
      `${API_BASE_URL}/imagens/historico/?email=${encodeURIComponent(userEmail)}`
    )
    if (response.ok) {
      const data = await response.json()
      if (data.success && Array.isArray(data.history)) {
        // Formata os campos date e time para o fuso horário exato do computador do usuário
        const formattedHistory = data.history.map((item) => {
          if (item.timestamp) {
            const itemDate = new Date(item.timestamp)
            const localDate = itemDate.toLocaleDateString('pt-BR', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric',
            })
            const localTime = itemDate.toLocaleTimeString('pt-BR', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })
            return {
              ...item,
              date: localDate,
              time: localTime,
            }
          }
          return item
        })

        // Atualiza o cache local com os dados vindos do banco de dados
        const key = `${HISTORY_PREFIX}${userEmail.toLowerCase()}`
        localStorage.setItem(key, JSON.stringify(formattedHistory))
        return formattedHistory
      }
    }
  } catch (e) {
    console.warn('Backend offline ou inacessível. Usando cache local:', e.message)
  }
  return getUserHistory(userEmail)
}

/**
 * Salva uma nova imagem no histórico do usuário (Local + REST API Django)
 */
export async function saveHistoryItem(userEmail, item) {
  const email = (userEmail || getCurrentUser()?.email || '').trim().toLowerCase()
  if (!email) return null

  const key = `${HISTORY_PREFIX}${email}`
  const currentList = getUserHistory(email)


  const now = new Date()
  const formattedDate = now.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
  const formattedTime = now.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

  const isSR =
    item.process === 'super-resolution' ||
    String(item.process || '').toLowerCase().includes('super-resolution') ||
    String(item.process || '').toLowerCase().includes('esc') ||
    String(item.process || '').toLowerCase().includes('dmnet')

  const isHdr =
    item.process === 'hdr' ||
    String(item.process || '').toLowerCase().includes('hdr')

  const isDehazing = !isSR && !isHdr

  const scale = item.scale ? Number(item.scale) : 2
  const rawDesc = (String(item.process || '') + ' ' + String(item.processLabel || '')).toLowerCase()
  const model = item.model || (rawDesc.includes('esc') ? 'ESC' : 'DMNet')
  const dehazingModel = item.dehazingModel || (rawDesc.includes('convir') ? 'ConvIR' : (item.model === 'ConvIR' ? 'ConvIR' : 'UDPNet'))
  const toneMapping = item.toneMapping || (
    rawDesc.includes('drago') ? 'Drago' :
    rawDesc.includes('mantiuk') ? 'Mantiuk' :
    (rawDesc.includes('log') || rawDesc.includes('mu-law')) ? 'Logarítmico' :
    'Reinhard'
  )

  const finalId = item.id || (item.db_id ? `db_${item.db_id}` : `hist_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`)

  const resolvedProcess = isSR ? 'super-resolution' : isHdr ? 'hdr' : 'dehazing'
  const resolvedProcessLabel = isSR
    ? `Super-Resolution (${model} ${scale}x)`
    : isHdr
    ? `HDR (${toneMapping})`
    : `Image Dehazing (${dehazingModel})`

  const newItem = {
    id: finalId,
    db_id: item.db_id || null,
    userEmail: userEmail.toLowerCase(),
    date: formattedDate,
    time: formattedTime,
    timestamp: item.timestamp || Date.now(),
    inputImage: item.inputImage, // Base64 dataURL da imagem original
    processedImage: item.processedImage || null, // Base64 dataURL da imagem processada
    process: resolvedProcess,
    scale: isSR ? scale : undefined,
    model: isSR ? model : (isDehazing ? dehazingModel : toneMapping),
    dehazingModel: isDehazing ? dehazingModel : undefined,
    toneMapping: isHdr ? toneMapping : undefined,
    processLabel: resolvedProcessLabel,
    fileName: item.fileName || 'imagem_upload.png',
    fileSize: item.fileSize || '1.0 MB',
    fileSizeInBytes: item.fileSizeInBytes || 0,
    dimensions: item.dimensions || null,
  }

  // 1. Deduplicação no LocalStorage: remove qualquer item pré-existente idêntico
  const filteredList = currentList.filter(
    (existing) =>
      existing.id !== newItem.id &&
      (!newItem.db_id || existing.db_id !== newItem.db_id)
  )

  const updatedList = [newItem, ...filteredList].slice(0, 50)
  localStorage.setItem(key, JSON.stringify(updatedList))

  // 2. Se a imagem já foi salva no backend durante a inferência (skipApiSave: true), não precisa reenviar
  if (item.skipApiSave) {
    return newItem
  }

  // 3. Envia para a API REST Django para persistir no banco de dados
  try {
    const apiResponse = await fetch(`${API_BASE_URL}/imagens/salvar/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: userEmail,
        inputImage: item.inputImage,
        processedImage: item.processedImage,
        process: newItem.process,
        scale: newItem.scale,
        model: newItem.model,
        toneMapping: newItem.toneMapping,
        fileName: item.fileName,
        fileSize: item.fileSize,
        dimensions: item.dimensions,
      }),
    })

    if (apiResponse.ok) {
      const apiData = await apiResponse.json()
      if (apiData.success && apiData.item) {
        newItem.db_id = apiData.item.db_id
        newItem.id = `db_${apiData.item.db_id}`
        // Atualiza o item no LocalStorage com o db_id
        const listWithDbId = getUserHistory(userEmail).map((it) =>
          it.id === finalId ? { ...it, db_id: apiData.item.db_id, id: `db_${apiData.item.db_id}` } : it
        )
        localStorage.setItem(key, JSON.stringify(listWithDbId))
      }
    }
  } catch (err) {
    console.warn('Aviso: Não foi possível salvar na API REST (usando persistência local):', err.message)
  }

  return newItem
}


/**
 * Remove um item do histórico do usuário (Local + REST API Django)
 */
export async function deleteHistoryItem(userEmail, itemId) {
  if (!userEmail || !itemId) return []
  const key = `${HISTORY_PREFIX}${userEmail.toLowerCase()}`
  const currentList = getUserHistory(userEmail)
  const itemToDelete = currentList.find((i) => i.id === itemId)

  const updatedList = currentList.filter((item) => item.id !== itemId)
  localStorage.setItem(key, JSON.stringify(updatedList))

  // Se tiver ID de banco de dados, remove no Django
  const dbId = itemToDelete?.db_id || (itemId.startsWith('db_') ? itemId.replace('db_', '') : null)
  if (dbId) {
    try {
      await fetch(`${API_BASE_URL}/imagens/${dbId}/`, {
        method: 'DELETE',
      })
    } catch (err) {
      console.warn('Erro ao deletar no backend:', err.message)
    }
  }

  return updatedList
}

/**
 * Limpa todo o histórico de um usuário (Local + REST API Django)
 */
export async function clearUserHistory(userEmail) {
  if (!userEmail) return
  const key = `${HISTORY_PREFIX}${userEmail.toLowerCase()}`
  localStorage.removeItem(key)

  try {
    await fetch(`${API_BASE_URL}/imagens/limpar/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email: userEmail }),
    })
  } catch (err) {
    console.warn('Erro ao limpar histórico no backend:', err.message)
  }
}

/**
 * Autenticação via REST API
 */
export async function loginWithApi(email, password) {
  try {
    const res = await fetch(`${API_BASE_URL}/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (res.ok) {
      const data = await res.json()
      if (data.success && data.user) {
        return setCurrentUser(data.user)
      }
    }
  } catch (e) {
    console.warn('Usando login offline:', e.message)
  }
  // Fallback offline
  const userName = email.includes('@') ? email.split('@')[0] : email
  return setCurrentUser({
    email,
    name: userName.charAt(0).toUpperCase() + userName.slice(1),
  })
}

/**
 * Cadastro via REST API
 */
export async function registerWithApi(name, email, password) {
  try {
    const res = await fetch(`${API_BASE_URL}/cadastro/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    })
    if (res.ok) {
      const data = await res.json()
      if (data.success && data.user) {
        return setCurrentUser(data.user)
      }
    }
  } catch (e) {
    console.warn('Usando cadastro offline:', e.message)
  }
  // Fallback offline
  return setCurrentUser({ name, email })
}
