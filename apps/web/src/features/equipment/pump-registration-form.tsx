import { zodResolver } from '@hookform/resolvers/zod'
import type { OperatingRegime, PumpCreate } from '@petrosense/shared-contracts'
import {
  MOUNTING_AXES,
  PUMP_STATUSES,
  PUMP_TYPES,
  SENSOR_TYPES,
} from '@petrosense/shared-contracts'
import { AlertCircle, Loader2, Radio, Waves } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormField } from '@/features/equipment/form-field'
import { ApiClientError } from '@/lib/api'

const codePattern = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/

const schema = z.object({
  pump_code: z
    .string()
    .trim()
    .min(1, 'Pump code is required.')
    .max(64, 'Pump code is too long.')
    .regex(codePattern, 'Use letters, numbers, dots, dashes or underscores.'),
  name: z.string().trim().min(1, 'Pump name is required.').max(160, 'Name is too long.'),
  pump_type: z.enum(PUMP_TYPES),
  location: z.string().trim().min(1, 'Laboratory location is required.').max(255),
  rated_speed_rpm: z
    .number()
    .int()
    .positive('Rated speed must be greater than zero.')
    .max(100_000),
  default_regime_id: z.string(),
  status: z.enum(PUMP_STATUSES),
  notes: z.string().max(2000, 'Notes are limited to 2000 characters.'),
  sensor_code: z
    .string()
    .trim()
    .min(1, 'Sensor code is required.')
    .max(64, 'Sensor code is too long.')
    .regex(codePattern, 'Use letters, numbers, dots, dashes or underscores.'),
  sensor_type: z.enum(SENSOR_TYPES),
  mounting_axis: z.enum(MOUNTING_AXES),
  mounting_position: z
    .string()
    .trim()
    .min(1, 'Mounting position is required.')
    .max(160),
  sampling_rate_hz: z
    .number()
    .positive('Sampling rate must be greater than zero.')
    .max(1_000_000),
  sensor_is_active: z.boolean(),
})

type FormValues = z.infer<typeof schema>

interface PumpRegistrationFormProps {
  regimes: OperatingRegime[]
  onSubmit: (payload: PumpCreate) => Promise<void>
  onCancel: () => void
}

function PumpRegistrationForm({ regimes, onSubmit, onCancel }: PumpRegistrationFormProps) {
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
      pump_code: '',
      name: '',
      pump_type: 'CENTRIFUGAL',
      location: 'Thermofluids Laboratory',
      rated_speed_rpm: 2900,
      default_regime_id: '',
      status: 'ACTIVE',
      notes: '',
      sensor_code: '',
      sensor_type: 'VIBRATION',
      mounting_axis: 'RADIAL_X',
      mounting_position: 'Drive-end bearing housing',
      sampling_rate_hz: 2048,
      sensor_is_active: true,
    },
  })

  async function submit(values: FormValues) {
    setServerError(null)
    const payload: PumpCreate = {
      pump_code: values.pump_code,
      name: values.name,
      pump_type: values.pump_type,
      location: values.location,
      rated_speed_rpm: values.rated_speed_rpm,
      default_regime_id: values.default_regime_id || null,
      status: values.status,
      notes: values.notes.trim() || null,
      sensor: {
        sensor_code: values.sensor_code,
        sensor_type: values.sensor_type,
        mounting_axis: values.mounting_axis,
        mounting_position: values.mounting_position,
        sampling_rate_hz: values.sampling_rate_hz,
        is_active: values.sensor_is_active,
      },
    }
    try {
      await onSubmit(payload)
    } catch (error) {
      setServerError({
        message:
          error instanceof ApiClientError
            ? error.message
            : 'The pump could not be registered. Check the local API and retry.',
        requestId: error instanceof ApiClientError ? error.requestId : null,
      })
    }
  }

  return (
    <form className="space-y-6" onSubmit={handleSubmit(submit)} noValidate>
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

      <section className="space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
          <Waves className="size-4 text-accent-600" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-navy-900">Pump identity</h3>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Pump ID"
            htmlFor="pump_code"
            error={errors.pump_code?.message}
            hint="Normalised to uppercase. Immutable after registration."
          >
            <Input
              id="pump_code"
              placeholder="LAB-PUMP-01"
              aria-invalid={Boolean(errors.pump_code)}
              {...register('pump_code')}
            />
          </FormField>
          <FormField label="Pump name" htmlFor="name" error={errors.name?.message}>
            <Input
              id="name"
              placeholder="Laboratory centrifugal pump"
              aria-invalid={Boolean(errors.name)}
              {...register('name')}
            />
          </FormField>
          <FormField label="Pump type" htmlFor="pump_type" error={errors.pump_type?.message}>
            <Select id="pump_type" {...register('pump_type')}>
              {PUMP_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type.replaceAll('_', ' ').toLowerCase()}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Equipment status" htmlFor="status" error={errors.status?.message}>
            <Select id="status" {...register('status')}>
              {PUMP_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status.charAt(0) + status.slice(1).toLowerCase()}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Laboratory location" htmlFor="location" error={errors.location?.message}>
            <Input
              id="location"
              placeholder="Thermofluids Laboratory"
              aria-invalid={Boolean(errors.location)}
              {...register('location')}
            />
          </FormField>
          <FormField
            label="Rated speed (RPM)"
            htmlFor="rated_speed_rpm"
            error={errors.rated_speed_rpm?.message}
          >
            <Input
              id="rated_speed_rpm"
              type="number"
              min="1"
              step="1"
              aria-invalid={Boolean(errors.rated_speed_rpm)}
              {...register('rated_speed_rpm', { valueAsNumber: true })}
            />
          </FormField>
          <FormField
            label="Default operating regime"
            htmlFor="default_regime_id"
            error={errors.default_regime_id?.message}
            hint="Used as the default label for new acquisition sessions."
          >
            <Select id="default_regime_id" {...register('default_regime_id')}>
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
          <FormField
            label="Notes"
            htmlFor="notes"
            error={errors.notes?.message}
            className="sm:col-span-2"
          >
            <Textarea
              id="notes"
              placeholder="Rig identity, restrictions, or commissioning notes"
              aria-invalid={Boolean(errors.notes)}
              {...register('notes')}
            />
          </FormField>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
          <Radio className="size-4 text-accent-600" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-navy-900">Initial vibration sensor</h3>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Sensor ID"
            htmlFor="sensor_code"
            error={errors.sensor_code?.message}
            hint="Unique across the deployment."
          >
            <Input
              id="sensor_code"
              placeholder="VIB-01"
              aria-invalid={Boolean(errors.sensor_code)}
              {...register('sensor_code')}
            />
          </FormField>
          <FormField
            label="Sensor type"
            htmlFor="sensor_type"
            error={errors.sensor_type?.message}
          >
            <Select id="sensor_type" {...register('sensor_type')}>
              {SENSOR_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type.toLowerCase()}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField
            label="Mounting axis"
            htmlFor="mounting_axis"
            error={errors.mounting_axis?.message}
          >
            <Select id="mounting_axis" {...register('mounting_axis')}>
              {MOUNTING_AXES.map((axis) => (
                <option key={axis} value={axis}>
                  {axis.replaceAll('_', ' ')}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField
            label="Mounting position"
            htmlFor="mounting_position"
            error={errors.mounting_position?.message}
          >
            <Input
              id="mounting_position"
              placeholder="Drive-end bearing housing"
              aria-invalid={Boolean(errors.mounting_position)}
              {...register('mounting_position')}
            />
          </FormField>
          <FormField
            label="Sampling rate (Hz)"
            htmlFor="sampling_rate_hz"
            error={errors.sampling_rate_hz?.message}
          >
            <Input
              id="sampling_rate_hz"
              type="number"
              min="1"
              step="1"
              aria-invalid={Boolean(errors.sampling_rate_hz)}
              {...register('sampling_rate_hz', { valueAsNumber: true })}
            />
          </FormField>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                className="size-4 rounded border-slate-300 text-accent-600 focus:ring-accent-500"
                {...register('sensor_is_active')}
              />
              Sensor active
            </label>
          </div>
        </div>
      </section>

      <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Registering…
            </>
          ) : (
            'Register pump and sensor'
          )}
        </Button>
      </div>
    </form>
  )
}

export { PumpRegistrationForm }
