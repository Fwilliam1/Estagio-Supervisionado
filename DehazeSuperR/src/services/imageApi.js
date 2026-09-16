/**
 * Serviço para processamento de imagens e integração com a IA no backend Django.
 */

const API_BASE_URL = 'http://127.0.0.1:8000/api'

export const imageApi = {
  /**
   * Executa a inferência de Super-Resolução com a rede neural (DMNet ou ESC) no backend.
   * @param {File} imageFile - Arquivo de imagem enviado pelo usuário.
   * @param {number} scale - Fator de ampliação (2, 3 ou 4).
   * @param {string} model - Arquitetura de rede ('DMNet' ou 'ESC').
   * @returns {Promise<Object>} Resultado da inferência com imagem Base64 e metadados.
   */
  async processSuperResolution(imageFile, scale = 2, model = 'DMNet') {
    const token = localStorage.getItem('dsr_token')
    if (!token) {
      throw new Error('Usuário não autenticado. Por favor, realize login novamente.')
    }

    const formData = new FormData()
    formData.append('imagem', imageFile)
    formData.append('scale', scale)
    formData.append('modelo', model)
    formData.append('model', model)
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
   * Executa a inferência de Dehazing (UDPNet ou ConvIR) no backend.
   * @param {File} imageFile - Arquivo de imagem enviado pelo usuário.
   * @param {string} model - Arquitetura de rede ('UDPNet' ou 'ConvIR').
   * @returns {Promise<Object>} Resultado da inferência com imagem Base64 e metadados.
   */
  async processDehazing(imageFile, model = 'UDPNet') {
    const token = localStorage.getItem('dsr_token')
    if (!token) {
      throw new Error('Usuário não autenticado. Por favor, realize login novamente.')
    }

    const formData = new FormData()
    formData.append('imagem', imageFile)
    formData.append('algoritmo', 'dehazing')
    formData.append('modelo', model)
    formData.append('model', model)

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
   * @param {string} toneMapping - Tipo de tone mapping ('Reinhard', 'Drago', 'Mantiuk', 'Logarítmico').
   * @returns {Promise<Object>} Resultado do processamento com imagem Base64 e metadados.
   */
  async processHdr(imageFile, toneMapping = 'Reinhard') {
    const token = localStorage.getItem('dsr_token')
    if (!token) {
      throw new Error('Usuário não autenticado. Por favor, realize login novamente.')
    }

    const formData = new FormData()
    formData.append('imagem', imageFile)
    formData.append('algoritmo', 'hdr')
    formData.append('tone_mapping', toneMapping)
    formData.append('toneMapping', toneMapping)
    formData.append('tonemap', toneMapping)

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


