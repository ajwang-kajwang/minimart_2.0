import { Pool } from 'pg';

// Create a connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: false, // Set to true if using SSL
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
});

export interface CameraData {
  id: number;
  time: Date;
  shopper_id: number;
  zone_id: number;
  x: number;
  y: number;
}

export interface ZoneDim {
  id: number;
  zone_name: string;
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
}

export interface SensorData {
  id: number;
  thing: string;
  temperature_c: number;
  pressure_hpa: number;
  humidity_rh: number;
  time: Date;
}

export interface ShelfCategory {
  shelf_name: string;
  category: string;
  display_order: number;
}

// Cache for shelf categories (refresh every 5 minutes)
let shelfCategoriesCache: { data: ShelfCategory[]; timestamp: number } | null = null;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

// Get shelf-to-category mapping from database
export async function getShelfCategories(): Promise<ShelfCategory[]> {
  // Return cached data if still valid
  if (shelfCategoriesCache && (Date.now() - shelfCategoriesCache.timestamp) < CACHE_TTL) {
    return shelfCategoriesCache.data;
  }

  const result = await pool.query(`
    SELECT shelf_name, category, display_order
    FROM minimart.shelf_categories
    ORDER BY display_order
  `);

  // Update cache
  shelfCategoriesCache = {
    data: result.rows,
    timestamp: Date.now(),
  };

  return result.rows;
}

// Get shelf categories as a map for quick lookup
export async function getShelfCategoriesMap(): Promise<Record<string, string>> {
  const categories = await getShelfCategories();
  return Object.fromEntries(categories.map(c => [c.shelf_name, c.category]));
}

// Get date range of available data
export async function getDataDateRange() {
  const result = await pool.query(`
    SELECT 
      MIN(time)::date as min_date, 
      MAX(time)::date as max_date,
      COUNT(DISTINCT shopper_id) as total_shoppers
    FROM minimart.camera_data
  `);
  return result.rows[0];
}

// Get total visitors in date range
export async function getTotalVisitors(startDate: string, endDate: string) {
  const result = await pool.query(`
    SELECT COUNT(DISTINCT shopper_id) as total
    FROM minimart.camera_data
    WHERE time::date BETWEEN $1 AND $2
  `, [startDate, endDate]);
  return parseInt(result.rows[0]?.total || '0');
}

// Get average dwell time in minutes
export async function getAvgDwellTime(startDate: string, endDate: string) {
  const result = await pool.query(`
    SELECT AVG(dwell_minutes) as avg_dwell
    FROM (
      SELECT 
        shopper_id,
        EXTRACT(EPOCH FROM (MAX(time) - MIN(time))) / 60 as dwell_minutes
      FROM minimart.camera_data
      WHERE time::date BETWEEN $1 AND $2
      GROUP BY shopper_id
      HAVING COUNT(*) > 1
    ) subq
  `, [startDate, endDate]);
  return parseFloat(result.rows[0]?.avg_dwell || '0');
}

// Get peak hour
export async function getPeakHour(startDate: string, endDate: string) {
  const result = await pool.query(`
    SELECT EXTRACT(HOUR FROM time) as hour, COUNT(*) as count
    FROM minimart.camera_data
    WHERE time::date BETWEEN $1 AND $2
    GROUP BY EXTRACT(HOUR FROM time)
    ORDER BY count DESC
    LIMIT 1
  `, [startDate, endDate]);
  return parseInt(result.rows[0]?.hour || '0');
}

// Get KPI comparison data (previous period)
export async function getKPIComparison(startDate: string, endDate: string) {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const daysDiff = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;

  // Calculate previous period
  const prevEnd = new Date(start);
  prevEnd.setDate(prevEnd.getDate() - 1);
  const prevStart = new Date(prevEnd);
  prevStart.setDate(prevStart.getDate() - daysDiff + 1);

  const prevStartStr = prevStart.toISOString().split('T')[0];
  const prevEndStr = prevEnd.toISOString().split('T')[0];

  // Get previous period KPIs
  const [prevVisitors, prevAvgDwell, prevAvgTemp] = await Promise.all([
    getTotalVisitors(prevStartStr, prevEndStr),
    getAvgDwellTime(prevStartStr, prevEndStr),
    getAvgTemperature(prevStartStr, prevEndStr),
  ]);

  // Get current period KPIs
  const [currVisitors, currAvgDwell, currAvgTemp] = await Promise.all([
    getTotalVisitors(startDate, endDate),
    getAvgDwellTime(startDate, endDate),
    getAvgTemperature(startDate, endDate),
  ]);

  // Calculate percentage changes
  const calcChange = (curr: number, prev: number): number | null => {
    if (prev === 0) return curr > 0 ? 100 : null;
    return ((curr - prev) / prev) * 100;
  };

  return {
    visitorsChange: calcChange(currVisitors, prevVisitors),
    dwellTimeChange: calcChange(currAvgDwell, prevAvgDwell),
    tempChange: currAvgTemp !== null && prevAvgTemp !== null
      ? currAvgTemp - prevAvgTemp
      : null,
    comparisonLabel: daysDiff === 1 ? 'vs yesterday' : 'vs prev period',
    prevPeriod: { start: prevStartStr, end: prevEndStr },
  };
}

// Get hourly traffic
export async function getHourlyTraffic(startDate: string, endDate: string) {
  const result = await pool.query(`
    SELECT 
      EXTRACT(HOUR FROM time) as hour,
      COUNT(DISTINCT shopper_id) as visitors
    FROM minimart.camera_data
    WHERE time::date BETWEEN $1 AND $2
    GROUP BY EXTRACT(HOUR FROM time)
    ORDER BY hour
  `, [startDate, endDate]);
  return result.rows;
}

// Get daily breakdown for multi-day queries
export async function getDailyBreakdown(startDate: string, endDate: string) {
  const result = await pool.query(`
    WITH daily_visitors AS (
      SELECT 
        "time"::date as visit_date,
        COUNT(DISTINCT shopper_id) as visitors
      FROM minimart.camera_data
      WHERE "time"::date BETWEEN $1 AND $2
      GROUP BY "time"::date
    ),
    daily_dwell AS (
      SELECT 
        visit_date,
        AVG(dwell_minutes) as avg_dwell
      FROM (
        SELECT 
          shopper_id,
          "time"::date as visit_date,
          EXTRACT(EPOCH FROM (MAX("time") - MIN("time"))) / 60 as dwell_minutes
        FROM minimart.camera_data
        WHERE "time"::date BETWEEN $1 AND $2
        GROUP BY shopper_id, "time"::date
        HAVING COUNT(*) > 1
      ) subq
      GROUP BY visit_date
    )
    SELECT 
      dv.visit_date as date,
      dv.visitors,
      dd.avg_dwell
    FROM daily_visitors dv
    LEFT JOIN daily_dwell dd ON dv.visit_date = dd.visit_date
    ORDER BY dv.visit_date
  `, [startDate, endDate]);
  return result.rows;
}

// Get zone performance
export async function getZonePerformance(startDate: string, endDate: string) {
  const result = await pool.query(`
    SELECT 
      TRIM(z.zone_name) as zone,
      COUNT(DISTINCT c.shopper_id) as visitors,
      COUNT(*) as events
    FROM minimart.camera_data c
    JOIN minimart.zone_dim z ON c.zone_id = z.id
    WHERE c.time::date BETWEEN $1 AND $2
    GROUP BY z.zone_name, z.id
    ORDER BY visitors DESC
  `, [startDate, endDate]);
  return result.rows;
}

// Get shelf performance (based on browsing behavior - facing_camera = 1)
// Improvements:
// 1. Uses boundary distance instead of center-point distance
// 2. Requires at least 2 consecutive records at same shelf to count as engagement
export async function getShelfPerformance(startDate: string, endDate: string) {
  const result = await pool.query(`
    WITH browsing_events AS (
      -- Get all browsing events with time ordering
      SELECT c.x, c.y, c.shopper_id, c.time,
             ROW_NUMBER() OVER (PARTITION BY c.shopper_id ORDER BY c.time) AS rn
      FROM minimart.camera_data c
      WHERE c.time::date BETWEEN $1 AND $2
        AND c.facing_camera = 1
    ),
    browsing_with_shelf AS (
      -- Find nearest shelf using boundary distance (not center distance)
      SELECT 
        b.shopper_id,
        b.time,
        b.rn,
        (SELECT TRIM(s.zone_name) 
         FROM minimart.zone_dim s 
         WHERE s.zone_name ILIKE 'Shelf%'
         ORDER BY 
           -- Boundary distance: distance to nearest edge of shelf rectangle
           SQRT(
             POW(GREATEST(0, s.x_min - b.x, b.x - s.x_max), 2) +
             POW(GREATEST(0, s.y_min - b.y, b.y - s.y_max), 2)
           )
         LIMIT 1) AS shelf_name
      FROM browsing_events b
    ),
    shelf_with_prev AS (
      -- Track shelf changes to identify consecutive stays
      SELECT 
        shopper_id,
        shelf_name,
        rn,
        LAG(shelf_name) OVER (PARTITION BY shopper_id ORDER BY rn) AS prev_shelf
      FROM browsing_with_shelf
      WHERE shelf_name IS NOT NULL
    ),
    consecutive_groups AS (
      -- Assign group ID when shelf changes
      SELECT *,
             SUM(CASE WHEN shelf_name != prev_shelf OR prev_shelf IS NULL THEN 1 ELSE 0 END) 
               OVER (PARTITION BY shopper_id ORDER BY rn) AS group_id
      FROM shelf_with_prev
    ),
    valid_engagements AS (
      -- Only count engagements with at least 2 consecutive records
      SELECT 
        shopper_id,
        shelf_name,
        group_id,
        COUNT(*) AS consecutive_count
      FROM consecutive_groups
      GROUP BY shopper_id, shelf_name, group_id
      HAVING COUNT(*) >= 2  -- At least 2 consecutive records (3-6 seconds)
    )
    SELECT 
      shelf_name as zone,
      COUNT(DISTINCT shopper_id) as visitors,
      COUNT(*) as events  -- Number of engagement sessions
    FROM valid_engagements
    GROUP BY shelf_name
    ORDER BY visitors DESC
  `, [startDate, endDate]);
  return result.rows;
}

// Get heatmap data - returns grid cells within each shelf for detailed heatmap
// Each shelf is divided into a grid (4 columns x 8 rows) for fine-grained visualization
export async function getHeatmapData(startDate: string, endDate: string) {
  const result = await pool.query(
    `WITH browsing_events AS (
        -- Find all events where customer is browsing (facing_camera = 1)
        SELECT c.x, c.y, c.shopper_id
        FROM minimart.camera_data c
        WHERE c.time::date BETWEEN $1 AND $2
          AND c.facing_camera = 1
      ),
      -- For each browsing event, find the nearest shelf and calculate grid position
      browsing_with_grid AS (
        SELECT 
          b.x, b.y, b.shopper_id,
          s.id AS shelf_id,
          TRIM(s.zone_name) AS shelf_name,
          -- Calculate grid cell within shelf (4 columns x 8 rows)
          LEAST(3, GREATEST(0, FLOOR((b.x - s.x_min) / ((s.x_max - s.x_min + 1)::float / 4))))::int AS grid_col,
          LEAST(7, GREATEST(0, FLOOR((b.y - s.y_min) / ((s.y_max - s.y_min + 1)::float / 8))))::int AS grid_row
        FROM browsing_events b
        CROSS JOIN LATERAL (
          SELECT id, zone_name, x_min, x_max, y_min, y_max
          FROM minimart.zone_dim 
          WHERE zone_name ILIKE 'Shelf%'
          ORDER BY ABS((x_min + x_max)/2 - b.x) + ABS((y_min + y_max)/2 - b.y)
          LIMIT 1
        ) s
      )
      SELECT 
        shelf_id AS zone_id,
        shelf_name,
        grid_col,
        grid_row,
        COUNT(*) AS count
      FROM browsing_with_grid
      WHERE shelf_id IS NOT NULL
      GROUP BY shelf_id, shelf_name, grid_col, grid_row
      ORDER BY shelf_id, grid_row, grid_col
    `,
    [startDate, endDate]
  );
  return result.rows;
}


export async function getShopperShelfPaths(startDate: string, endDate: string) {
  const result = await pool.query(
    `WITH ordered AS (
        SELECT c.shopper_id, c.time, c.x, c.y, c.facing_camera, TRIM(z.zone_name) AS zone
        FROM minimart.camera_data c
        JOIN minimart.zone_dim z ON c.zone_id = z.id
        WHERE c.time::date BETWEEN $1 AND $2
      ),
      -- Find the nearest shelf for each browsing event (facing_camera = 1)
      browsing_with_shelf AS (
        SELECT o.shopper_id, o.time, o.x, o.y, o.zone,
               (SELECT TRIM(s.zone_name) 
                FROM minimart.zone_dim s 
                WHERE s.zone_name ILIKE 'Shelf%'
                ORDER BY ABS((s.x_min + s.x_max)/2 - o.x) + ABS((s.y_min + s.y_max)/2 - o.y)
                LIMIT 1) AS nearest_shelf
        FROM ordered o
        WHERE o.facing_camera = 1
      ),
      -- Detect shelf changes (when customer moves to a different shelf)
      shelf_events AS (
        SELECT shopper_id, time, nearest_shelf AS zone,
               LAG(nearest_shelf) OVER(PARTITION BY shopper_id ORDER BY time) AS prev_zone
        FROM browsing_with_shelf
        WHERE nearest_shelf IS NOT NULL
      ),
      shelf_changes AS (
        SELECT shopper_id, time, zone
        FROM shelf_events
        WHERE prev_zone IS DISTINCT FROM zone
      ),
      point_paths AS (
        SELECT shopper_id,
               JSON_AGG(JSON_BUILD_OBJECT('x', x, 'y', y, 'time', time, 'zone', zone) ORDER BY time) AS points
        FROM ordered
        GROUP BY shopper_id
      ),
      shelf_paths AS (
        SELECT shopper_id,
               JSON_AGG(JSON_BUILD_OBJECT('zone', zone, 'time', time) ORDER BY time) AS shelves
        FROM shelf_changes
        GROUP BY shopper_id
      )
    SELECT p.shopper_id,
           p.points,
           COALESCE(s.shelves, '[]'::json) AS shelves
    FROM point_paths p
    LEFT JOIN shelf_paths s ON p.shopper_id = s.shopper_id
    ORDER BY p.shopper_id
    `,
    [startDate, endDate]
  );
  return result.rows;
}

// Get zone definitions
export async function getZones() {
  const result = await pool.query(`
    SELECT id, TRIM(zone_name) as zone_name, x_min, x_max, y_min, y_max
    FROM minimart.zone_dim
  `);
  return result.rows;
}

// Get sensor data averages
export async function getSensorAverages(startDate: string, endDate: string) {
  const result = await pool.query(`
    SELECT 
      ROUND(AVG(temperature_c)::numeric, 1) as avg_temp,
      ROUND(AVG(humidity_rh)::numeric, 1) as avg_humidity
    FROM minimart.sensor_data
    WHERE time::date BETWEEN $1 AND $2
  `, [startDate, endDate]);
  return result.rows[0];
}

// Get average temperature for comparison
export async function getAvgTemperature(startDate: string, endDate: string): Promise<number | null> {
  const result = await pool.query(`
    SELECT ROUND(AVG(temperature_c)::numeric, 1) as avg_temp
    FROM minimart.sensor_data
    WHERE time::date BETWEEN $1 AND $2
  `, [startDate, endDate]);
  const temp = result.rows[0]?.avg_temp;
  return temp !== null && temp !== undefined ? parseFloat(temp) : null;
}

// ============================================================
// Aggregation Table Functions (for AI features)
// ============================================================

export interface DailySummary {
  date: string;
  total_records: number;      // Count of tracking data records (position events)
  unique_shoppers: number;
  avg_dwell_minutes: number;
  peak_hour: number;
  hourly_traffic: Array<{ hour: number; count: number }>;
  zone_ranking: Array<{ zone: string; visitors: number; events: number }>;
  top_zones: string[];
  avg_zones_visited: number;
  avg_temp: number | null;
  visitors_vs_yesterday: number | null;
  visitors_vs_last_week: number | null;
}

export interface DailyAiInsights {
  date: string;
  summary: string;
  highlights: string[];
  recommendations: string[];
  anomalies: string[];
  model_used: string;
  tokens_used: number;
}
// Get daily summary from aggregation table (supports date range)
export async function getDailySummary(startDate: string, endDate?: string): Promise<DailySummary | null> {
  // If no endDate or same as startDate, return single day
  if (!endDate || startDate === endDate) {
    const result = await pool.query(`
      SELECT 
        date, total_records, unique_shoppers, avg_dwell_minutes, peak_hour,
        hourly_traffic, zone_ranking, top_zones, avg_zones_visited,
        avg_temp, visitors_vs_yesterday, visitors_vs_last_week
      FROM minimart.daily_summary
      WHERE date = $1
    `, [startDate]);
    return result.rows[0] || null;
  }

  // Multi-day range: aggregate data with simplified query
  const result = await pool.query(`
    WITH aggregated AS (
      SELECT 
        SUM(total_records)::int as total_records,
        SUM(unique_shoppers)::int as unique_shoppers,
        AVG(avg_dwell_minutes)::numeric(10,2) as avg_dwell_minutes,
        AVG(avg_zones_visited)::numeric(10,2) as avg_zones_visited,
        AVG(avg_temp)::numeric(10,1) as avg_temp
      FROM minimart.daily_summary
      WHERE date BETWEEN $1 AND $2
    ),
    latest_day AS (
      SELECT peak_hour, top_zones
      FROM minimart.daily_summary
      WHERE date BETWEEN $1 AND $2
      ORDER BY date DESC
      LIMIT 1
    )
    SELECT 
      $1::date as date,
      a.total_records,
      a.unique_shoppers,
      a.avg_dwell_minutes,
      l.peak_hour,
      NULL::jsonb as hourly_traffic,
      NULL::jsonb as zone_ranking,
      l.top_zones,
      a.avg_zones_visited,
      a.avg_temp,
      NULL::numeric as visitors_vs_yesterday,
      NULL::numeric as visitors_vs_last_week
    FROM aggregated a, latest_day l
  `, [startDate, endDate]);

  return result.rows[0] || null;
}

// Get real-time summary directly from camera_data (when aggregated table is empty)
export async function getRealTimeSummary(startDate: string, endDate?: string): Promise<DailySummary | null> {
  const effectiveEndDate = endDate || startDate;

  const result = await pool.query(`
    WITH daily_stats AS (
      SELECT 
        COUNT(*) AS total_records,
        COUNT(DISTINCT shopper_id) AS unique_shoppers
      FROM minimart.camera_data
      WHERE time::date BETWEEN $1 AND $2
    ),
    dwell_stats AS (
      SELECT 
        ROUND(AVG(EXTRACT(EPOCH FROM (max_t - min_t)) / 60)::numeric, 2) AS avg_dwell_minutes
      FROM (
        SELECT 
          shopper_id,
          MIN(time) AS min_t,
          MAX(time) AS max_t
        FROM minimart.camera_data
        WHERE time::date BETWEEN $1 AND $2
        GROUP BY shopper_id
        HAVING COUNT(*) > 1
      ) shopper_times
    ),
    peak_hour AS (
      SELECT EXTRACT(HOUR FROM time)::int AS peak_hour
      FROM minimart.camera_data
      WHERE time::date BETWEEN $1 AND $2
      GROUP BY EXTRACT(HOUR FROM time)
      ORDER BY COUNT(*) DESC
      LIMIT 1
    ),
    zone_ranking AS (
      SELECT 
        ARRAY_AGG(zone_name ORDER BY visitors DESC) FILTER (WHERE rn <= 3) AS top_zones
      FROM (
        SELECT 
          TRIM(z.zone_name) AS zone_name,
          COUNT(DISTINCT c.shopper_id) AS visitors,
          ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT c.shopper_id) DESC) AS rn
        FROM minimart.camera_data c
        JOIN minimart.zone_dim z ON c.zone_id = z.id
        WHERE c.time::date BETWEEN $1 AND $2
        GROUP BY z.zone_name
      ) ranked
    ),
    path_stats AS (
      SELECT 
        ROUND(AVG(zones_count)::numeric, 1) AS avg_zones_visited
      FROM (
        SELECT shopper_id, COUNT(DISTINCT zone_id) AS zones_count
        FROM minimart.camera_data
        WHERE time::date BETWEEN $1 AND $2
        GROUP BY shopper_id
      ) paths
    ),
    sensor_stats AS (
      SELECT 
        ROUND(AVG(temperature_c)::numeric, 1) AS avg_temp
      FROM minimart.sensor_data
      WHERE time::date BETWEEN $1 AND $2
    )
    SELECT 
      $1::date AS date,
      ds.total_records,
      ds.unique_shoppers,
      COALESCE(dw.avg_dwell_minutes, 0) AS avg_dwell_minutes,
      ph.peak_hour,
      NULL::jsonb AS hourly_traffic,
      NULL::jsonb AS zone_ranking,
      zr.top_zones,
      ps.avg_zones_visited,
      ss.avg_temp,
      NULL::numeric AS visitors_vs_yesterday,
      NULL::numeric AS visitors_vs_last_week
    FROM daily_stats ds
    CROSS JOIN dwell_stats dw
    CROSS JOIN peak_hour ph
    CROSS JOIN zone_ranking zr
    CROSS JOIN path_stats ps
    CROSS JOIN sensor_stats ss
  `, [startDate, effectiveEndDate]);

  const row = result.rows[0];
  // Return null if no records found
  if (!row || row.total_records === 0 || row.total_records === '0') {
    return null;
  }
  return row;
}

// Get hourly summary for a date range
export async function getHourlySummary(startDate: string, endDate: string) {
  const result = await pool.query(`
    SELECT 
      date, hour, total_records, unique_shoppers,
      avg_dwell_minutes, zone_visitors, avg_temp
    FROM minimart.hourly_summary
    WHERE date BETWEEN $1 AND $2
    ORDER BY date, hour
  `, [startDate, endDate]);
  return result.rows;
}

// Get cached AI insights for a date
export async function getDailyAiInsights(date: string): Promise<DailyAiInsights | null> {
  const result = await pool.query(`
    SELECT 
      date, summary, highlights, recommendations, anomalies,
      model_used, tokens_used
    FROM minimart.daily_ai_insights
    WHERE date = $1
  `, [date]);
  return result.rows[0] || null;
}

// Save AI-generated insights
export async function saveDailyAiInsights(insights: {
  date: string;
  summary: string;
  highlights: string[];
  recommendations: string[];
  anomalies?: string[];
  model_used: string;
  prompt_tokens: number;
  completion_tokens: number;
}): Promise<void> {
  await pool.query(`
    INSERT INTO minimart.daily_ai_insights (
      date, summary, highlights, recommendations, anomalies,
      model_used, tokens_used, prompt_tokens, completion_tokens, updated_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
    ON CONFLICT (date) DO UPDATE SET
      summary = EXCLUDED.summary,
      highlights = EXCLUDED.highlights,
      recommendations = EXCLUDED.recommendations,
      anomalies = EXCLUDED.anomalies,
      model_used = EXCLUDED.model_used,
      tokens_used = EXCLUDED.tokens_used,
      prompt_tokens = EXCLUDED.prompt_tokens,
      completion_tokens = EXCLUDED.completion_tokens,
      updated_at = NOW()
  `, [
    insights.date,
    insights.summary,
    insights.highlights,
    insights.recommendations,
    insights.anomalies || [],
    insights.model_used,
    insights.prompt_tokens + insights.completion_tokens,
    insights.prompt_tokens,
    insights.completion_tokens,
  ]);
}

// Determine data source based on date range
export function selectDataSource(startDate: string, endDate: string): 'raw' | 'hourly' | 'daily' {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const daysDiff = Math.ceil((today.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
  const rangeDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

  // Use raw data for today or very recent (within 1 day)
  if (daysDiff <= 1) return 'raw';

  // Use hourly for short ranges within last week
  if (daysDiff <= 7 && rangeDays <= 3) return 'hourly';

  // Use daily for everything else
  return 'daily';
}

export default pool;

