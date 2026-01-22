import pytest
import sys
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.main import main

@pytest.mark.asyncio
async def test_main_arguments():
    """Test that main parses arguments and calls async_main correctly via asyncio.run."""
    test_args = ['src.main', 'https://example.com', '--concurrency', '20', '--output', 'test_out.csv', '--rate-limit', '10']
    
    with patch.object(sys, 'argv', test_args):
        # We need mock_run to await the coroutine to avoid RuntimeWarning
        async def mock_run_side_effect(coro):
             await coro 
            
        with patch('asyncio.run', new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = mock_run_side_effect
            
            with patch('src.main.async_main', new_callable=AsyncMock) as mock_async_main:
                # Since asyncio.run is mocked as async, main() will try to call it synchronously?
                # Wait, main() calls asyncio.run(...) which is sync function.
                # So we cannot mock asyncio.run with AsyncMock if main() calls it normally.
                # main() calls `asyncio.run(coro)`. This returns result.
                # If we mock it, we need a sync mock that does `asyncio.run` logic or just closes the coro.
                pass 
                
    # Better approach: Just close the coroutine in side_effect of a sync mock
    with patch.object(sys, 'argv', test_args):
         with patch('asyncio.run') as mock_run:
            mock_run.side_effect = lambda coro: coro.close() # Close to avoid warning
            
            with patch('src.main.async_main', new_callable=AsyncMock) as mock_async_main:
                main()
                
                mock_run.assert_called_once()
                args, _ = mock_async_main.call_args
                parsed_args = args[0]
                assert parsed_args.url == 'https://example.com'
                assert parsed_args.concurrency == 20
                assert parsed_args.output == 'test_out.csv'
                assert parsed_args.rate_limit == 10.0

def test_main_defaults():
    """Test default arguments."""
    test_args = ['src.main', 'https://example.com']
    
    with patch.object(sys, 'argv', test_args):
         with patch('asyncio.run') as mock_run:
            mock_run.side_effect = lambda coro: coro.close() # Close to avoid warning
            
            with patch('src.main.async_main', new_callable=AsyncMock) as mock_async_main:
                main()
                
                mock_run.assert_called_once()
                args, _ = mock_async_main.call_args
                parsed_args = args[0]
                assert parsed_args.url == 'https://example.com'
                assert parsed_args.concurrency == 10
                assert parsed_args.output == 'results.csv'
                assert parsed_args.rate_limit == 5.0

def test_main_invalid_url():
    """Test invalid URL scheme."""
    test_args = ['src.main', 'ftp://example.com']
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1

def test_main_invalid_concurrency():
    """Test invalid concurrency (zero or negative)."""
    test_args = ['src.main', 'https://example.com', '--concurrency', '0']
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1

def test_main_invalid_rate_limit():
    """Test invalid rate limit (zero or negative)."""
    test_args = ['src.main', 'https://example.com', '--rate-limit', '-5']
    
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
