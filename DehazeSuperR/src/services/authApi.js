/**
 * Serviço de API de Autenticação para integração do frontend React com o backend Django.
 */

const API_BASE_URL = 'http://127.0.0.1:8000/api'

export const authApi = {
  /**
   * Realiza o cadastro de um novo usuário no backend.
   * @param {Object} param0
   * @param {string} param0.name
   * @param {string} param0.email
   * @param {string} param0.password
   * @param {string} param0.confirmPassword
   */
  async cadastrar({ name, email, password, confirmPassword }) {
    try {
      const response = await fetch(`${API_BASE_URL}/cadastrar/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nome: name,
          email: email,
          senha: password,
          confirmacao_senha: confirmPassword,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.mensagem || 'Erro ao realizar cadastro.')
      }

      return data
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Não foi possível conectar ao servidor backend (Django). Verifique se ele está em execução em http://127.0.0.1:8000.')
      }
      throw error
    }
  },

  /**
   * Realiza login no backend e armazena o token JWT de 2h no localStorage.
   * @param {Object} param0
   * @param {string} param0.email
   * @param {string} param0.password
   */
  async login({ email, password }) {
    try {
      const response = await fetch(`${API_BASE_URL}/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          senha: password,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.mensagem || 'Credenciais inválidas. Verifique seu e-mail e senha.')
      }

      if (data.token) {
        localStorage.setItem('dsr_token', data.token)
        localStorage.setItem('dsr_user', JSON.stringify(data.dados))
      }

      return data
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Não foi possível conectar ao servidor backend (Django). Verifique se ele está em execução em http://127.0.0.1:8000.')
      }
      throw error
    }
  },

  /**
   * Encerra a sessão no backend (invalidando o token) e limpa o localStorage.
   */
  async logout() {
    const token = localStorage.getItem('dsr_token')
    try {
      if (token) {
        await fetch(`${API_BASE_URL}/logout/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        })
      }
    } catch (e) {
      console.warn('Erro ao notificar logout no backend:', e)
    } finally {
      localStorage.removeItem('dsr_token')
      localStorage.removeItem('dsr_user')
    }
  },

  /**
   * Valida o token atual e obtém os dados do usuário autenticado.
   */
  async getMe() {
    const token = localStorage.getItem('dsr_token')
    if (!token) return null

    try {
      const response = await fetch(`${API_BASE_URL}/me/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.status === 401) {
        localStorage.removeItem('dsr_token')
        localStorage.removeItem('dsr_user')
        return null
      }

      const data = await response.json()
      if (response.ok && data.dados) {
        localStorage.setItem('dsr_user', JSON.stringify(data.dados))
        return data.dados
      }
      return null
    } catch (e) {
      console.warn('Erro ao validar sessão com backend:', e)
      return null
    }
  },

  /**
   * Retorna os dados do usuário salvos localmente.
   */
  getCurrentUser() {
    const userStr = localStorage.getItem('dsr_user')
    try {
      return userStr ? JSON.parse(userStr) : null
    } catch {
      return null
    }
  },

  /**
   * Retorna o token JWT salvo no localStorage.
   */
  getToken() {
    return localStorage.getItem('dsr_token')
  },

  /**
   * Verifica se existe um token salvo.
   */
  isAuthenticated() {
    return !!localStorage.getItem('dsr_token')
  },
}
