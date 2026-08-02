// ----- auth middleware tests @ backend/internal/auth/middleware_test.go -----
package auth

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/clerkinc/clerk-sdk-go/clerk"
	"github.com/go-jose/go-jose/v3/jwt"
	"github.com/stretchr/testify/assert"
)

type mockVerifier struct {
	claims *clerk.SessionClaims
	err    error
}

func (m *mockVerifier) VerifyToken(_ string, _ ...clerk.VerifyTokenOption) (*clerk.SessionClaims, error) {
	return m.claims, m.err
}

func TestRequireAuthNoHeader(t *testing.T) {
	mw := RequireAuth(&mockVerifier{})

	handler := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("handler should not be called")
	}))

	req := httptest.NewRequest("GET", "/", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)

	var resp map[string]string
	json.NewDecoder(w.Body).Decode(&resp)
	assert.Equal(t, "unauthorized", resp["detail"])
}

func TestRequireAuthInvalidToken(t *testing.T) {
	mw := RequireAuth(&mockVerifier{err: errors.New("invalid token")})

	handler := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("handler should not be called")
	}))

	req := httptest.NewRequest("GET", "/", nil)
	req.Header.Set("Authorization", "Bearer garbage")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestRequireAuthNonBearerHeader(t *testing.T) {
	mw := RequireAuth(&mockVerifier{})

	handler := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("handler should not be called")
	}))

	req := httptest.NewRequest("GET", "/", nil)
	req.Header.Set("Authorization", "Basic abc123")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestRequireAuthValidTokenPassesUserID(t *testing.T) {
	mw := RequireAuth(&mockVerifier{
		claims: &clerk.SessionClaims{
			Claims: jwt.Claims{
				Subject: "user_abc123",
			},
			SessionID: "sess_xyz",
		},
	})

	var capturedUserID string
	handler := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedUserID = UserIDFromContext(r.Context())
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "user_abc123", capturedUserID)
}

func TestRequireAuthEmptyToken(t *testing.T) {
	mw := RequireAuth(&mockVerifier{err: errors.New("empty token")})

	handler := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("handler should not be called")
	}))

	req := httptest.NewRequest("GET", "/", nil)
	req.Header.Set("Authorization", "Bearer ")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}
