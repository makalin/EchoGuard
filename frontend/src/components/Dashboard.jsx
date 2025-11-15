import React, { useState, useEffect } from 'react'
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Chip,
} from '@mui/material'
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { format } from 'date-fns'
import api from '../services/api'

function Dashboard() {
  const [mapData, setMapData] = useState({ detections: [] })
  const [stats, setStats] = useState(null)
  const [hydrophones, setHydrophones] = useState({ hydrophones: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
    const interval = setInterval(loadDashboardData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const loadDashboardData = async () => {
    try {
      const [mapRes, statsRes, hydrophonesRes] = await Promise.all([
        api.get('/dashboard/map-data?days=7'),
        api.get('/detections/stats/summary?days=7'),
        api.get('/dashboard/hydrophones'),
      ])
      setMapData(mapRes.data)
      setStats(statsRes.data)
      setHydrophones(hydrophonesRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error loading dashboard data:', error)
      setLoading(false)
    }
  }

  const getEventColor = (eventType, isThreat) => {
    if (isThreat) {
      switch (eventType) {
        case 'blast_fishing':
          return 'red'
        case 'vessel':
          return 'orange'
        case 'seismic':
          return 'purple'
        default:
          return 'red'
      }
    }
    return 'blue'
  }

  const center = mapData.detections.length > 0
    ? [mapData.detections[0].latitude, mapData.detections[0].longitude]
    : [0, 0]

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {loading ? (
        <Typography>Loading...</Typography>
      ) : (
        <>
          {/* Statistics Cards */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Detections
                  </Typography>
                  <Typography variant="h4">
                    {stats?.total_detections || 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Threat Detections
                  </Typography>
                  <Typography variant="h4" color="error">
                    {stats?.threat_detections || 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Marine Life
                  </Typography>
                  <Typography variant="h4" color="primary">
                    {stats?.by_event_type?.marine_life || 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Period
                  </Typography>
                  <Typography variant="h6">
                    Last {stats?.period_days || 7} days
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Map */}
          <Paper sx={{ p: 2, mb: 3, height: '500px' }}>
            <Typography variant="h6" gutterBottom>
              Detection Map
            </Typography>
            <MapContainer
              center={center}
              zoom={2}
              style={{ height: '450px', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              {hydrophones.hydrophones.map((h) => (
                <Marker key={h.id} position={[h.latitude, h.longitude]}>
                  <Popup>
                    <strong>{h.name}</strong>
                    <br />
                    Depth: {h.depth}m
                  </Popup>
                </Marker>
              ))}
              {mapData.detections.map((det) => (
                <CircleMarker
                  key={det.id}
                  center={[det.latitude, det.longitude]}
                  radius={8}
                  color={getEventColor(det.type, det.is_threat)}
                  fillColor={getEventColor(det.type, det.is_threat)}
                  fillOpacity={0.6}
                >
                  <Popup>
                    <strong>{det.type}</strong>
                    <br />
                    Confidence: {(det.confidence * 100).toFixed(1)}%
                    <br />
                    {det.is_threat && <Chip label="THREAT" color="error" size="small" />}
                    <br />
                    {format(new Date(det.timestamp), 'PPpp')}
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </Paper>

          {/* Event Type Distribution */}
          {stats?.by_event_type && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Detection Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={Object.entries(stats.by_event_type).map(([name, value]) => ({ name, value }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          )}
        </>
      )}
    </Box>
  )
}

export default Dashboard

