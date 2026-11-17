import { Compass } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Navigation"
        title="Page not found"
        description="The requested route does not exist in this prototype."
        badge={<Badge variant="neutral">404</Badge>}
      />
      <Card>
        <CardContent className="p-5">
          <EmptyState
            icon={Compass}
            title="This route is not part of the screen map"
            description="Use the sidebar to open the dashboard or one of the twelve research screens."
            action={
              <Button variant="secondary" onClick={() => navigate('/dashboard')}>
                Return to dashboard
              </Button>
            }
          />
        </CardContent>
      </Card>
    </div>
  )
}

export { NotFoundPage }
