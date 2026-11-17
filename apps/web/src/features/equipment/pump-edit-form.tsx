import { zodResolver } from '@hookform/resolvers/zod'
import type {
  OperatingRegime,
  Pump,
  PumpStatus,
  PumpType,
  PumpUpdate,
} from '@petrosense/shared-contracts'
import { PUMP_STATUSES, PUMP_TYPES } from '@petrosense/shared-contracts'
import { AlertCircle, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormField } from '@/features/equipment/form-field'
import { ApiClientError } from '@/lib/api'

const schema = z.object({
  name: z.string().trim().min(1, 'Pump name is required.').max(160),
  pump_type: z.enum(PUMP_TYPES),
  location: z.string().trim().min(1, 'Location is required.').max(255),
  rated_speed_rpm: z.number().int().positive().max(100_000),
  default_regime_id: z.string(),
  status: z.enum(PUMP_STATUSES),
  notes: z.string().max(2000),
})

type FormValues = z.infer<typeof schema>

interface PumpEditFormProps {
  pump: Pump
  regimes: OperatingRegime[]
  onSubmit: (payload: PumpUpdate) => Promise<void>
  onCancel: () => void
}

function PumpEditForm({ pump, regimes, onSubmit, onCancel }: PumpEditFormProps) {
  const [serverError, setServerError] = useState<{
    message: string
    requestId: string | null
  } | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: pump.name,
      pump_type: pump.pump_type,
      location: pump.location,
      rated_speed_rpm: pump.rated_speed_rpm,
      default_regime_id: pump.default_regime?.id ?? '',
      status: pump.status,
      notes: pump.notes ?? '',
    },
  })

  async function submit(values: FormValues) {
    setServerError(null)
    try {
      await onSubmit({
        name: values.name,
        pump_type: values.pump_type as PumpType,
        location: values.location,
        rated_speed_rpm: values.rated_speed_rpm,
        default_regime_id: values.default_regime_id || null,
        status: values.status as PumpStatus,
        notes: values.notes.trim() || null,
      })
    } catch (error) {
      setServerError({
        message:
          error instanceof ApiClientError
            ? error.message
            : 'The pump could not be updated. Check the local API and retry.',
        requestId: error instanceof ApiClientError ? error.requestId : null,
      })
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit(submit)} noValidate>
      {serverError ? (
        <div
          role="alert"
          className="flex gap-2.5 rounded-lg border border-red-200 bg-fault-soft px-3.5 py-3 text-sm text-red-800"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <div className="space-y-1">
            <p className="font-medium">{serverError.message}</p>
            {serverError.requestId ? (
              <p className="font-mono text-[10px] text-red-700/70">
                Request ID: {serverError.requestId}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2 text-xs text-slate-500">
        Pump ID <span className="font-mono font-semibold text-navy-900">{pump.pump_code}</span>{' '}
        is immutable. {pump.sensors.length} sensor
        {pump.sensors.length === 1 ? '' : 's'} assigned.
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Pump name" htmlFor="edit-name" error={errors.name?.message}>
          <Input
            id="edit-name"
            aria-invalid={Boolean(errors.name)}
            {...register('name')}
          />
        </FormField>
        <FormField label="Pump type" htmlFor="edit-pump_type" error={errors.pump_type?.message}>
          <Select id="edit-pump_type" {...register('pump_type')}>
            {PUMP_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.replaceAll('_', ' ').toLowerCase()}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField label="Location" htmlFor="edit-location" error={errors.location?.message}>
          <Input
            id="edit-location"
            aria-invalid={Boolean(errors.location)}
            {...register('location')}
          />
        </FormField>
        <FormField
          label="Rated speed (RPM)"
          htmlFor="edit-rated_speed_rpm"
          error={errors.rated_speed_rpm?.message}
        >
          <Input
            id="edit-rated_speed_rpm"
            type="number"
            min="1"
            step="1"
            aria-invalid={Boolean(errors.rated_speed_rpm)}
            {...register('rated_speed_rpm', { valueAsNumber: true })}
          />
        </FormField>
        <FormField
          label="Default operating regime"
          htmlFor="edit-default_regime_id"
          error={errors.default_regime_id?.message}
        >
          <Select id="edit-default_regime_id" {...register('default_regime_id')}>
            <option value="">No default regime</option>
            {regimes
              .filter((regime) => regime.is_active)
              .map((regime) => (
                <option key={regime.id} value={regime.id}>
                  {regime.name}
                </option>
              ))}
          </Select>
        </FormField>
        <FormField label="Equipment status" htmlFor="edit-status" error={errors.status?.message}>
          <Select id="edit-status" {...register('status')}>
            {PUMP_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status.charAt(0) + status.slice(1).toLowerCase()}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField
          label="Notes"
          htmlFor="edit-notes"
          error={errors.notes?.message}
          className="sm:col-span-2"
        >
          <Textarea id="edit-notes" aria-invalid={Boolean(errors.notes)} {...register('notes')} />
        </FormField>
      </div>

      <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Saving…
            </>
          ) : (
            'Save pump'
          )}
        </Button>
      </div>
    </form>
  )
}

export { PumpEditForm }
