"""Parallel session management."""

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable

from puppets.session import Session
from puppets.exceptions import PuppetsError

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages multiple parallel browser sessions.
    
    This class handles running multiple sessions concurrently using
    thread pools. Each session gets its own Tor instance and browser.
    
    Attributes:
        max_workers: Maximum number of parallel sessions.
        headless: Whether to run browsers in headless mode.
        tor_timeout: Timeout for Tor startup per session.
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        headless: bool = False,
        tor_timeout: int = 120,
    ):
        """Initialize the session manager.
        
        Args:
            max_workers: Maximum number of parallel sessions.
            headless: Whether to run browsers in headless mode.
            tor_timeout: Timeout for Tor startup per session.
        """
        self.max_workers = max_workers
        self.headless = headless
        self.tor_timeout = tor_timeout
    
    def run_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Run a single session.
        
        Args:
            session_id: Optional custom session ID.
            
        Returns:
            Dictionary with session results.
        """
        session = Session(
            session_id=session_id,
            headless=self.headless,
            tor_timeout=self.tor_timeout,
        )
        
        try:
            return session.run()
        except Exception as exc:
            return {
                "session_id": session.session_id,
                "success": False,
                "error": str(exc),
            }
        finally:
            session.cleanup()
    
    def run_sessions(
        self,
        num_sessions: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Run multiple sessions in parallel.
        
        Args:
            num_sessions: Number of sessions to run.
            progress_callback: Optional callback(completed, total) for progress.
            
        Returns:
            List of result dictionaries, one per session.
        """
        results: List[Dict[str, Any]] = []
        completed = 0
        
        logger.info(f"Starting {num_sessions} sessions with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all sessions
            futures = {}
            for i in range(num_sessions):
                session_id = f"session_{i+1}_{uuid.uuid4().hex[:6]}"
                future = executor.submit(self.run_session, session_id)
                futures[future] = session_id
            
            # Collect results as they complete
            for future in as_completed(futures):
                session_id = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    logger.error(f"Session {session_id} raised exception: {exc}")
                    results.append({
                        "session_id": session_id,
                        "success": False,
                        "error": str(exc),
                    })
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, num_sessions)
                else:
                    logger.info(f"Completed {completed}/{num_sessions} sessions")
        
        # Summary
        successful = sum(1 for r in results if r.get("success", False))
        logger.info(
            f"All sessions completed: {successful}/{num_sessions} successful"
        )
        
        return results
    
    def run_continuous(
        self,
        duration_seconds: int = 3600,
        interval_seconds: int = 10,
    ) -> List[Dict[str, Any]]:
        """Run sessions continuously for a duration.
        
        Args:
            duration_seconds: Total time to run.
            interval_seconds: Time between session starts.
            
        Returns:
            List of all session results.
        """
        import time
        
        results: List[Dict[str, Any]] = []
        start_time = time.time()
        session_num = 0
        
        logger.info(f"Starting continuous mode for {duration_seconds} seconds")
        
        while time.time() - start_time < duration_seconds:
            session_num += 1
            session_id = f"continuous_{session_num}_{uuid.uuid4().hex[:6]}"
            
            logger.info(f"Starting session {session_num}...")
            result = self.run_session(session_id)
            results.append(result)
            
            # Wait before next session
            if time.time() - start_time + interval_seconds < duration_seconds:
                time.sleep(interval_seconds)
        
        successful = sum(1 for r in results if r.get("success", False))
        logger.info(
            f"Continuous mode ended: {successful}/{len(results)} successful"
        )
        
        return results