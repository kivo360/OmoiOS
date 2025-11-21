import { useState } from 'react'
import { TicketPanel } from './components/TicketPanel'

type Ticket = {
  id: string
  title: string
  description: string
  workspaceDir: string
  aiSummary?: string | null
}

const sampleTickets: Ticket[] = [
  {
    id: 'T-123',
    title: 'Add /health endpoint',
    description: 'Add a /health endpoint that returns JSON {status, version} and wire it into the router.',
    workspaceDir: '/tmp/workspace-t123',
  },
  {
    id: 'T-124',
    title: 'Implement user authentication',
    description: 'Create a login system with JWT tokens and password hashing.',
    workspaceDir: '/tmp/workspace-t124',
  },
]

function App() {
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(sampleTickets[0])

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Ticket Panel Prototype</h1>
        
        <div className="grid grid-cols-2 gap-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">Tickets</h2>
            <div className="space-y-2">
              {sampleTickets.map((ticket) => (
                <button
                  key={ticket.id}
                  onClick={() => setSelectedTicket(ticket)}
                  className={`w-full text-left p-3 rounded border ${
                    selectedTicket?.id === ticket.id
                      ? 'bg-blue-50 border-blue-300'
                      : 'bg-white border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-semibold">{ticket.id}</div>
                  <div className="text-sm text-gray-600">{ticket.title}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            {selectedTicket && <TicketPanel ticket={selectedTicket} />}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

