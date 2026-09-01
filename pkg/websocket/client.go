package websocket

import (
	"context"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
)

type Client struct {
	conn    *websocket.Conn
	url     string
	timeout time.Duration
}

func NewClient(url string, timeoutSeconds int) *Client {
	return &Client{
		url:     url,
		timeout: time.Duration(timeoutSeconds) * time.Second,
	}
}

func (c *Client) Connect(ctx context.Context) error {
	dialer := websocket.Dialer{
		HandshakeTimeout: c.timeout,
	}

	conn, _, err := dialer.DialContext(ctx, c.url, http.Header{})
	if err != nil {
		return err
	}

	c.conn = conn
	return nil
}

func (c *Client) ReadMessage(ctx context.Context) ([]byte, error) {
	if c.conn == nil {
		return nil, websocket.ErrCloseSent
	}

	c.conn.SetReadDeadline(time.Now().Add(c.timeout))

	msgCh := make(chan []byte, 1)
	errCh := make(chan error, 1)

	go func() {
		_, msg, err := c.conn.ReadMessage()
		if err != nil {
			errCh <- err
			return
		}
		msgCh <- msg
	}()

	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case err := <-errCh:
		return nil, err
	case msg := <-msgCh:
		return msg, nil
	}
}

func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

func (c *Client) IsConnected() bool {
	return c.conn != nil
}

// SetReadDeadline 设置读取超时。
func (c *Client) SetReadDeadline(t time.Time) error {
	if c.conn != nil {
		return c.conn.SetReadDeadline(t)
	}
	return nil
}