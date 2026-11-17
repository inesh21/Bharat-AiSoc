package com.offlinecrop.assistant.data

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import kotlinx.coroutines.flow.Flow

/**
 * Scan history entity stored in local SQLite database via Room (Task C10).
 * Persists offline scan results with full Contract 1 and Contract 3 JSON payloads.
 */
@Entity(tableName = "scan_history")
data class ScanRecord(
    @PrimaryKey val id: String,
    val timestamp: Long,
    val crop: String,
    val diagnosis: String,
    val severityBand: String,
    val confidence: Float,
    val imagePath: String?,
    val visionJson: String,
    val advisoryJson: String
)

@Dao
interface ScanHistoryDao {
    @Query("SELECT * FROM scan_history ORDER BY timestamp DESC")
    fun getAllScans(): Flow<List<ScanRecord>>

    @Query("SELECT * FROM scan_history WHERE id = :id LIMIT 1")
    suspend fun getScanById(id: String): ScanRecord?

    @Insert
    suspend fun insertScan(record: ScanRecord)

    @Query("DELETE FROM scan_history WHERE id = :id")
    suspend fun deleteScan(id: String)

    @Query("DELETE FROM scan_history")
    suspend fun clearHistory()
}

@Database(entities = [ScanRecord::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun scanHistoryDao(): ScanHistoryDao
}
