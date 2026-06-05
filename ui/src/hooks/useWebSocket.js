// ui/src/hooks/useWebSocket.js
import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { connectWS } from '../api'

export function useWebSocket() {
  const qc  = useQueryClient()
  const ref = useRef(null)

  useEffect(() => {
    ref.current = connectWS((msg) => {
      // Cuando Jarvis hace algo, refrescamos los datos automáticamente
      if (['lead_created','lead_updated','lead_status_changed'].includes(msg.event)) {
        qc.invalidateQueries({ queryKey: ['leads'] })
        qc.invalidateQueries({ queryKey: ['stats'] })
      }
      if (msg.event === 'new_message') {
        qc.invalidateQueries({ queryKey: ['conversations', msg.data.lead_id] })
      }
    })
    return () => ref.current?.close()
  }, [qc])
}