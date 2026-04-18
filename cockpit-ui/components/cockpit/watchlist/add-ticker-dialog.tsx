'use client'

import { type FormEvent, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

interface AddTickerDialogProps {
  open: boolean
  onClose: () => void
  onSubmit: (input: { ticker: string; note: string; stance: string }) => Promise<void>
  error: string | null
}

export function AddTickerDialog({
  open,
  onClose,
  onSubmit,
  error,
}: AddTickerDialogProps) {
  const [ticker, setTicker] = useState('')
  const [note, setNote] = useState('')
  const [stance, setStance] = useState('watch')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    try {
      await onSubmit({ ticker, note, stance })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add to watchlist</DialogTitle>
          <DialogDescription>
            Add a ticker with an optional note and stance.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <Label htmlFor="ticker">Ticker</Label>
            <Input
              id="ticker"
              value={ticker}
              onChange={(event) => setTicker(event.target.value)}
              placeholder="CBA.AX"
              required
            />
          </div>
          <div>
            <Label htmlFor="note">Note</Label>
            <Textarea
              id="note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="stance">Stance</Label>
            <Input
              id="stance"
              value={stance}
              onChange={(event) => setStance(event.target.value)}
            />
          </div>
          {error ? <div className="text-sm text-destructive">{error}</div> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              Add
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
