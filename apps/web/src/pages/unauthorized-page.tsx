import type { Role } from '@petrosense/shared-contracts'
import { ShieldX } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useAuth } from '@/providers/auth-provider'
import { formatRole } from '@/lib/utils'

interface UnauthorizedPageProps {
  requiredRoles?: Role[]
}

function UnauthorizedPage({ requiredRoles }: UnauthorizedPageProps) {
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Access control"
        title="Restricted area"
        description="The backend rejected this view for your current role. Navigation visibility is not the security boundary."
        badge={<Badge variant="fault">403 · Forbidden</Badge>}
      />
      <Card>
        <CardContent className="p-5">
          <EmptyState
            icon={ShieldX}
            title="Your role does not permit this screen"
            description={`Signed in as ${user ? formatRole(user.role) : 'an unknown role'}. Contact the research administrator if you need a different level of access.`}
            action={
              <div className="flex flex-col items-center gap-3">
                {requiredRoles && requiredRoles.length > 0 ? (
                  <div className="flex flex-wrap items-center justify-center gap-1.5">
                    <span className="text-[11px] text-slate-500">Required:</span>
                    {requiredRoles.map((role) => (
                      <Badge key={role} variant="outline" className="font-medium">
                        {formatRole(role)}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                <Button variant="secondary" onClick={() => navigate('/dashboard')}>
                  Return to dashboard
                </Button>
              </div>
            }
          />
        </CardContent>
      </Card>
    </div>
  )
}

export { UnauthorizedPage }
