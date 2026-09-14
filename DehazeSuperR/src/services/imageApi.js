/**
 * Serviço para processamento de imagens e integração com a IA no backend Django.
 */

const API_BASE_URL = 'http://127.0.0.1:8000/api'

export const imageApi = {
  /**
   * Executa a inferência de Super-Resolução com a rede neural ESC no backend.
   * @param {File} imageFile - Arquivo de imagem enviado pelo usuário.
   * @param {number} scale - Fator de ampliação (2, 3 ou 4).
   * @returns {Promise<Object>} Resultado da inferência com imagem Base64 e metadados.
   */
  async processSuperResolution(imageFile, scale = 2) {
    const token = localStorage.getItem('dsr_token')
    if (!token) {
      throw new Error('Usuário não autenticado. Por favor, realize login novamente.')
    }

    const formData = new FormData()
    formData.append('imagem', imageFile)
    formData.append('scale', scale)
    formData.append('algoritmo', 'super-resolution')

    try {
      const response = await fetch(`${API_BASE_URL}/processar/super-resolution/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.mensagem || 'Erro ao processar a imagem com a rede neural.')
      }

      return data
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Não foi possível conectar ao servidor backend (Django). Verifique se ele está rodando.')
      }
      throw error
    }
  },

  /**
   * Executa a inferência de Dehazing com Depth Anything V2 + UDPNet no backend.
   * @param {File} imageFile - Arquivo de imagem enviado pelo usuário.
   * @returns {Promise<Object>} Resultado da inferência com imagem Base64 e metadados.
   */
  async processDehazing(imageFile) {
    const token = localStorage.getItem('dsr_token')
    if (!token) {
      throw new Error('Usuário não autenticado. Por favor, realize login novamente.')
    }

    const formData = new FormData()
    formData.append('imagem', imageFile)
    formData.append('algoritmo', 'dehazing')

    try {
      const response = await fetch(`${API_BASE_URL}/processar/dehazing/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.mensagem || 'Erro ao processar a imagem com a rede neural de Dehazing.')
      }

      return data
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Não foi possível conectar ao servidor backend (Django). Verifique se ele está rodando.')
      }
      throw error
    }
  },

  /**
   * Executa a inferência ou processamento de HDR no backend.
   * @param {File} imageFile - Arquivo de imagem enviado pelo usuário.
   * @returns {Promise<Object>} Resultado do processamento com imagem Base64 e metadados.
   */
  async processHdr(imageFile) {
    const token = localStorage.getItem('dsr_token')
    if (!token) {
      throw new Error('Usuário não autenticado. Por favor, realize login novamente.')
    }

    const formData = new FormData()
    formData.append('imagem', imageFile)
    formData.append('algoritmo', 'hdr')

    try {
      const response = await fetch(`${API_BASE_URL}/processar/hdr/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.mensagem || 'Erro ao processar a imagem com o algoritmo de HDR.')
      }

      return data
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Não foi possível conectar ao servidor backend (Django). Verifique se ele está rodando.')
      }
      throw error
    }
  },
}


