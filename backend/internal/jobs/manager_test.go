// ----- job manager tests @ backend/internal/jobs/manager_test.go -----
package jobs

import (
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
)

func setTestRedis(addr string) {
	rdb = redis.NewClient(&redis.Options{Addr: addr})
}

func setupRedis(t *testing.T) *miniredis.Miniredis {
	t.Helper()
	mr := miniredis.RunT(t)
	oldRdb := rdb
	t.Cleanup(func() { rdb = oldRdb })
	setTestRedis(mr.Addr())
	return mr
}

func TestCreateJob(t *testing.T) {
	mr := setupRedis(t)
	defer mr.Close()

	jobID, err := CreateJob("test_task", map[string]interface{}{"key": "value"})
	assert.NoError(t, err)
	assert.NotEmpty(t, jobID)

	job, err := GetJob(jobID)
	assert.NoError(t, err)
	assert.NotNil(t, job)
	assert.Equal(t, "queued", job.Status)
	assert.Equal(t, "test_task", job.TaskName)
}

func TestGetJobNotFound(t *testing.T) {
	mr := setupRedis(t)
	defer mr.Close()

	job, err := GetJob("nonexistent")
	assert.NoError(t, err)
	assert.Nil(t, job)
}

func TestUpdateJob(t *testing.T) {
	mr := setupRedis(t)
	defer mr.Close()

	jobID, _ := CreateJob("test", nil)
	err := UpdateJob(jobID, map[string]interface{}{"status": "processing"})
	assert.NoError(t, err)

	job, _ := GetJob(jobID)
	assert.Equal(t, "processing", job.Status)
}

func TestAddJobError(t *testing.T) {
	mr := setupRedis(t)
	defer mr.Close()

	jobID, _ := CreateJob("test", nil)
	err := AddJobError(jobID, "something went wrong")
	assert.NoError(t, err)

	job, _ := GetJob(jobID)
	assert.Len(t, job.Errors, 1)
	assert.Contains(t, job.Errors[0], "something went wrong")
}
