#pragma once
#include <afxmt.h>

class CAppLog
{
public:
    static CAppLog* GetInstance();
    static void ReleaseInstance();

    void Write(LPCTSTR szFunc, LPCTSTR szFmt, ...);
    void WriteV(LPCTSTR szFunc, LPCTSTR szFmt, va_list args);

private:
    CAppLog();
    ~CAppLog();

    void WriteFile(LPCTSTR szFunc, LPCTSTR szBuffer);
    CString GetLogDir();
    CString GetLogFileName(int nDay);

    static CAppLog*         m_pInstance;
    static CCriticalSection m_InstanceLock;
    CCriticalSection        m_csLog;
};

void AppLog(LPCTSTR szFunc, LPCTSTR szFmt, ...);
