import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Send, Bot, User, MessageSquare } from 'lucide-react'
import { getChatSessions, createChatSession, deleteChatSession,
         getChatMessages, streamChatMessage } from '../api'

export default function Chat() {
  const queryClient = useQueryClient()
  const [sessionId,  setSessionId]  = useState(null)
  const [messages,   setMessages]   = useState([])
  const [input,      setInput]      = useState('')
  const [streaming,  setStreaming]  = useState(false)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  const { data: sessions = [] } = useQuery({
    queryKey: ['chat-sessions'],
    queryFn:  getChatSessions,
  })

  // Al cargar, seleccionar la sesión más reciente o crear una
  useEffect(() => {
    if (!sessionId && sessions.length > 0) {
      selectSession(sessions[0].id)
    }
  }, [sessions])

  const selectSession = async (id) => {
    setSessionId(id)
    const msgs = await getChatMessages(id)
    setMessages(msgs)
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
  }

  const newSessionMutation = useMutation({
    mutationFn: () => createChatSession('Nueva conversación'),
    onSuccess: (session) => {
      queryClient.invalidateQueries(['chat-sessions'])
      setSessionId(session.id)
      setMessages([])
      inputRef.current?.focus()
    },
  })

  const deleteSessionMutation = useMutation({
    mutationFn: (id) => deleteChatSession(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries(['chat-sessions'])
      if (id === sessionId) {
        setSessionId(null)
        setMessages([])
      }
    },
  })

  const send = async () => {
    if (!input.trim() || streaming || !sessionId) return
    const text = input.trim()
    setInput('')

    // Mensaje usuario (optimista)
    const tmpUser = { id: `u-${Date.now()}`, role: 'user', content: text }
    // Placeholder asistente
    const tmpId   = `a-${Date.now()}`
    const tmpAsst = { id: tmpId, role: 'assistant', content: '', _streaming: true }
    setMessages(prev => [...prev, tmpUser, tmpAsst])
    setStreaming(true)
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 30)

    try {
      const res = await streamChatMessage(sessionId, text)
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          try {
            const obj = JSON.parse(raw)
            if (obj.done) {
              setMessages(prev => prev.map(m =>
                m.id === tmpId ? { ...m, _streaming: false } : m
              ))
              queryClient.invalidateQueries(['chat-sessions'])
            } else if (obj.delta) {
              setMessages(prev => prev.map(m =>
                m.id === tmpId ? { ...m, content: m.content + obj.delta } : m
              ))
              bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
            }
          } catch {}
        }
      }
    } catch (err) {
      setMessages(prev => prev.map(m =>
        m.id === tmpId
          ? { ...m, content: 'Error al conectar con Jarvis.', _streaming: false }
          : m
      ))
    } finally {
      setStreaming(false)
    }
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className="flex h-full">

      {/* Panel de sesiones */}
      <aside className="w-56 bg-jarvis-surface border-r border-jarvis-border flex flex-col flex-shrink-0">
        <div className="px-3 py-3 border-b border-jarvis-border">
          <button
            onClick={() => newSessionMutation.mutate()}
            className="w-full flex items-center gap-2 px-3 py-2 bg-[#FF8C00] hover:bg-[#e07d00]
                       rounded-lg text-sm font-semibold text-white transition-colors shadow-[#FF8C00]/20 shadow-md">
            <Plus size={14} /> Nueva conversación
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
          {sessions.length === 0 && (
            <p className="text-xs text-jarvis-muted px-2 py-4 text-center">Sin conversaciones</p>
          )}
          {sessions.map(s => (
            <div key={s.id}
              onClick={() => selectSession(s.id)}
              className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors
                         ${s.id === sessionId
                           ? 'bg-[#FF8C00]/15 border border-[#FF8C00]/25'
                           : 'hover:bg-jarvis-card border border-transparent'
                         }`}>
              <MessageSquare size={12} className={s.id === sessionId ? 'text-[#FF8C00]' : 'text-jarvis-muted'} />
              <span className={`flex-1 text-xs truncate font-medium
                               ${s.id === sessionId ? 'text-[#FF8C00]' : 'text-jarvis-muted group-hover:text-jarvis-text'}`}>
                {s.title}
              </span>
              <button
                onClick={e => { e.stopPropagation(); deleteSessionMutation.mutate(s.id) }}
                className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 text-jarvis-muted transition-opacity">
                <Trash2 size={10} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Área de chat */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Header */}
        <div className="px-5 py-3.5 border-b border-jarvis-border bg-jarvis-surface/50 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#FF8C00]/15 border border-[#FF8C00]/25 flex items-center justify-center">
            <Bot size={15} className="text-[#FF8C00]" />
          </div>
          <div>
            <div className="text-sm font-semibold text-jarvis-text">Asistente Jarvis</div>
            <div className="text-[10px] text-jarvis-muted">
              {streaming ? (
                <span className="text-teal-400 animate-pulse">Escribiendo...</span>
              ) : 'Análisis comercial · CRM · Estrategia'}
            </div>
          </div>
        </div>

        {/* Mensajes */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          {!sessionId && (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[#FF8C00]/10 border border-[#FF8C00]/20
                              flex items-center justify-center">
                <Bot size={28} className="text-[#FF8C00]" />
              </div>
              <div>
                <p className="font-heading font-bold text-jarvis-text text-lg">Jarvis listo</p>
                <p className="text-jarvis-muted text-sm mt-1">
                  Preguntame sobre leads, estrategia o campañas.<br/>
                  Usá el botón para empezar.
                </p>
              </div>
              <button onClick={() => newSessionMutation.mutate()}
                className="px-4 py-2 bg-[#FF8C00] hover:bg-[#e07d00] rounded-lg text-sm
                           font-semibold text-white transition-colors">
                Nueva conversación
              </button>
            </div>
          )}

          {messages.map(m => (
            <div key={m.id} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>

              {/* Avatar */}
              <div className={`w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center
                              ${m.role === 'user'
                                ? 'bg-jarvis-card border border-jarvis-border'
                                : 'bg-[#FF8C00]/15 border border-[#FF8C00]/25'
                              }`}>
                {m.role === 'user'
                  ? <User size={13} className="text-jarvis-muted" />
                  : <Bot  size={13} className="text-[#FF8C00]" />
                }
              </div>

              {/* Burbuja */}
              <div className={`max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed
                              ${m.role === 'user'
                                ? 'bg-[#FF8C00]/15 border border-[#FF8C00]/20 text-jarvis-text'
                                : 'bg-jarvis-card border border-jarvis-border text-jarvis-text'
                              }`}>
                {m.content || (m._streaming && (
                  <span className="flex gap-1 items-center py-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-jarvis-muted animate-bounce" style={{animationDelay:'0ms'}} />
                    <span className="w-1.5 h-1.5 rounded-full bg-jarvis-muted animate-bounce" style={{animationDelay:'150ms'}} />
                    <span className="w-1.5 h-1.5 rounded-full bg-jarvis-muted animate-bounce" style={{animationDelay:'300ms'}} />
                  </span>
                ))}
                {m._streaming && m.content && (
                  <span className="inline-block w-0.5 h-4 bg-[#FF8C00] animate-pulse ml-0.5 align-middle" />
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-5 py-4 border-t border-jarvis-border bg-jarvis-surface/30">
          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={!sessionId || streaming}
              placeholder={sessionId ? 'Preguntale a Jarvis...' : 'Creá una conversación primero'}
              rows={1}
              style={{ resize: 'none' }}
              className="flex-1 bg-jarvis-card border border-jarvis-border rounded-xl px-4 py-3
                         text-sm text-jarvis-text placeholder-jarvis-muted/50
                         focus:outline-none focus:border-[#FF8C00]/50 transition-colors
                         disabled:opacity-40 max-h-32 overflow-y-auto"
              onInput={e => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px'
              }}
            />
            <button
              onClick={send}
              disabled={!input.trim() || !sessionId || streaming}
              className="p-3 bg-[#FF8C00] hover:bg-[#e07d00] rounded-xl text-white
                         transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                         shadow-lg shadow-[#FF8C00]/20 flex-shrink-0">
              <Send size={15} />
            </button>
          </div>
          <p className="text-[10px] text-jarvis-muted/50 mt-2 text-center">
            Enter para enviar · Shift+Enter para nueva línea
          </p>
        </div>
      </div>
    </div>
  )
}
