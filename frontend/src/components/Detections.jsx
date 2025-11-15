import React, { useState, useEffect } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Chip,
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  CircularProgress,
} from '@mui/material'
import { format } from 'date-fns'
import api from '../services/api'

function Detections() {
  const [detections, setDetections] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    event_type: '',
    is_threat: '',
  })

  useEffect(() => {
    loadDetections()
  }, [filters])

  const loadDetections = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filters.event_type) params.append('event_type', filters.event_type)
      if (filters.is_threat !== '') params.append('is_threat', filters.is_threat)
      
      const response = await api.get(`/detections/?${params.toString()}`)
      setDetections(response.data)
    } catch (error) {
      console.error('Error loading detections:', error)
    } finally {
      setLoading(false)
    }
  }

  const getEventTypeColor = (eventType) => {
    switch (eventType) {
      case 'blast_fishing':
        return 'error'
      case 'vessel':
        return 'warning'
      case 'seismic':
        return 'secondary'
      case 'marine_life':
        return 'info'
      default:
        return 'default'
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Detections
      </Typography>

      {/* Filters */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Event Type</InputLabel>
          <Select
            value={filters.event_type}
            label="Event Type"
            onChange={(e) => setFilters({ ...filters, event_type: e.target.value })}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="blast_fishing">Blast Fishing</MenuItem>
            <MenuItem value="vessel">Vessel</MenuItem>
            <MenuItem value="seismic">Seismic</MenuItem>
            <MenuItem value="marine_life">Marine Life</MenuItem>
            <MenuItem value="ambient">Ambient</MenuItem>
          </Select>
        </FormControl>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Threat Status</InputLabel>
          <Select
            value={filters.is_threat}
            label="Threat Status"
            onChange={(e) => setFilters({ ...filters, is_threat: e.target.value })}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="true">Threats Only</MenuItem>
            <MenuItem value="false">Non-Threats Only</MenuItem>
          </Select>
        </FormControl>
        <Button variant="outlined" onClick={loadDetections}>
          Refresh
        </Button>
      </Box>

      {/* Detections Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Timestamp</TableCell>
              <TableCell>Event Type</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Threat</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Hydrophone</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : detections.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No detections found
                </TableCell>
              </TableRow>
            ) : (
              detections.map((det) => (
                <TableRow key={det.id}>
                  <TableCell>{det.id}</TableCell>
                  <TableCell>
                    {format(new Date(det.timestamp), 'PPpp')}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={det.event_type}
                      color={getEventTypeColor(det.event_type)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {(det.confidence * 100).toFixed(1)}%
                  </TableCell>
                  <TableCell>
                    {det.is_threat ? (
                      <Chip label="THREAT" color="error" size="small" />
                    ) : (
                      <Chip label="Safe" color="success" size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    {det.latitude && det.longitude
                      ? `${det.latitude.toFixed(4)}, ${det.longitude.toFixed(4)}`
                      : 'N/A'}
                  </TableCell>
                  <TableCell>{det.hydrophone_name || 'N/A'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default Detections

