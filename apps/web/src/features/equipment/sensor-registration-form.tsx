import { zodResolver } from '@hookform/resolvers/zod'
import type {
  Pump,
  SensorRegister,
  SensorType,
  MountingAxis,
} from '@petrosense/shared-contracts'
import { MOUNTING_AXES, SENSOR_TYPES } from '@petrosense/shared-contracts'
import { AlertCircle, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { FormField } from '@/features/equipment/form-field'
import { ApiClientError } from '@/lib/api'

const codePattern = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/

const schema = z.object({
  sensor_code: z
    .string()
    .trim()
    .min(1, 'Sensor code is required.')
    .max(64)
    .regex(codePattern, 'Use letters, numbers, dots, dashes or underscores.'),
  pump_id: z.string().min(1, 'Select a pump.'),
  sensor_type: z.enum(SENSOR_TYPES),
  manufacturer: z.string().max(120),
  model_name: z.string().max(120),
  mounting_axis: z.enum(MOUNTING_AXES),
  mounting_position: z.string().trim().min(1, 'Mounting position is required.').max(160),
  sampling_rate_hz: z.number().positive().max(1_000_000),
  is_active: z.boolean(),
})

type FormValues = z.infer<typeof schema>

interface SensorRegistrationFormProps {
  pumps: Pump[]
  defaultPumpId?: string
  onSubmit: (payload: SensorRegister) => Promise<void>
  onCancel: () => void
}

function SensorRegistrationForm({
  pumps,
  defaultPumpId,
  onSubmit,
  onCancel,
}: SensorRegistrationFormProps) {
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
      sensor_code: '',
      pump_id: defaultPumpId ?? pumps[0]?.id ?? '',
      sensor_type: 'VIBRATION',
      manufacturer: '',
      model_name: '',
      mounting_axis: 'RADIAL_X',
      mounting_position: '',
      sampling_rate_hz: 2048,
      is_active: true,
    },
  })

  async function submit(values: FormValues) {
    setServerError(null)
    try {
      await onSubmit({
        sensor_code: values.sensor_code,
        pump_id: values.pump_id,
        sensor_type: values.sensor_type as SensorType,
        manufacturer: values.manufacturer.trim() || null,
        model_name: values.model_name.trim() || null,
        mounting_axis: values.mounting_axis as MountingAxis,
        mounting_position: values.mounting_position,
        sampling_rate_hz: values.sampling_rate_hz,
        is_active: values.is_active,
      })
    } catch (error) {
      setServerError({
        message:
          error instanceof ApiClientError
            ? error.message
            : 'The sensor could not be registered. Check the local API and retry.',
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

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          label="Sensor ID"
          htmlFor="sensor-form-code"
          error={errors.sensor_code?.message}
        >
          <Input
            id="sensor-form-code"
            placeholder="VIB-02"
            aria-invalid={Boolean(errors.sensor_code)}
            {...register('sensor_code')}
          />
        </FormField>
        <FormField label="Assigned pump" htmlFor="sensor-form-pump" error={errors.pump_id?.message}>
          <Select id="sensor-form-pump" {...register('pump_id')}>
            {pumps.map((pump) => (
              <option key={pump.id} value={pump.id}>
                {pump.pump_code} — {pump.name}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField
          label="Sensor type"
          htmlFor="sensor-form-type"
          error={errors.sensor_type?.message}
        >
          <Select id="sensor-form-type" {...register('sensor_type')}>
            {SENSOR_TYPES.map((type) => (
              <option key={type} value={type}>
                {type.toLowerCase()}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField
          label="Mounting axis"
          htmlFor="sensor-form-axis"
          error={errors.mounting_axis?.message}
        >
          <Select id="sensor-form-axis" {...register('mounting_axis')}>
            {MOUNTING_AXES.map((axis) => (
              <option key={axis} value={axis}>
                {axis.replaceAll('_', ' ')}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField
          label="Mounting position"
          htmlFor="sensor-form-position"
          error={errors.mounting_position?.message}
        >
          <Input
            id="sensor-form-position"
            placeholder="Drive-end bearing housing"
            aria-invalid={Boolean(errors.mounting_position)}
            {...register('mounting_position')}
          />
        </FormField>
        <FormField
          label="Sampling rate (Hz)"
          htmlFor="sensor-form-rate"
          error={errors.sampling_rate_hz?.message}
        >
          <Input
            id="sensor-form-rate"
            type="number"
            min="1"
            step="1"
            aria-invalid={Boolean(errors.sampling_rate_hz)}
            {...register('sampling_rate_hz', { valueAsNumber: true })}
          />
        </FormField>
        <FormField
          label="Manufacturer"
          htmlFor="sensor-form-manufacturer"
          error={errors.manufacturer?.message}
        >
          <Input id="sensor-form-manufacturer" {...register('manufacturer')} />
        </FormField>
        <FormField
          label="Model"
          htmlFor="sensor-form-model"
          error={errors.model_name?.message}
        >
          <Input id="sensor-form-model" {...register('model_name')} />
        </FormField>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              className="size-4 rounded border-slate-300 text-accent-600 focus:ring-accent-500"
              {...register('is_active')}
            />
            Sensor active
          </label>
        </div>
      </div>

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
            'Register sensor'
          )}
        </Button>
      </div>
    </form>
  )
}

export { SensorRegistrationForm }
