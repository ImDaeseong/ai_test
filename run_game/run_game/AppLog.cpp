#include "stdafx.h"
#include "AppLog.h"
#include <io.h>

CAppLog* CAppLog::m_pInstance = NULL;
CCriticalSection CAppLog::m_InstanceLock;

CAppLog* CAppLog::GetInstance()
{
    CSingleLock lock(&m_InstanceLock, TRUE);
    if (m_pInstance == NULL)
        m_pInstance = new CAppLog();
    return m_pInstance;
}

void CAppLog::ReleaseInstance()
{
    CSingleLock lock(&m_InstanceLock, TRUE);
    if (m_pInstance != NULL)
    {
        delete m_pInstance;
        m_pInstance = NULL;
    }
}

CAppLog::CAppLog()
{
}

CAppLog::~CAppLog()
{
}

void CAppLog::Write(LPCTSTR szFunc, LPCTSTR szFmt, ...)
{
    va_list args;
    va_start(args, szFmt);
    WriteV(szFunc, szFmt, args);
    va_end(args);
}

void CAppLog::WriteV(LPCTSTR szFunc, LPCTSTR szFmt, va_list args)
{
    CSingleLock lock(&m_csLog, TRUE);

    TCHAR szBuffer[4096];
    memset(szBuffer, 0, sizeof(szBuffer));
    _vsntprintf_s(szBuffer, _countof(szBuffer), _TRUNCATE, szFmt, args);

    WriteFile(szFunc, szBuffer);
}

void AppLog(LPCTSTR szFunc, LPCTSTR szFmt, ...)
{
    va_list args;
    va_start(args, szFmt);
    CAppLog::GetInstance()->WriteV(szFunc, szFmt, args);
    va_end(args);
}

void CAppLog::WriteFile(LPCTSTR szFunc, LPCTSTR szBuffer)
{
    CTime theTime = CTime::GetCurrentTime();
    CString strFile = GetLogFileName(theTime.GetDay());

    static int nHour = 0;
    if (nHour != theTime.GetHour())
    {
        CTimeSpan theTimeSpan(1, 0, 0, 0);
        CTime theNextDay = theTime + theTimeSpan;
        CString strExpiredFile = GetLogFileName(theNextDay.GetDay());

        TRY
        {
            if (_taccess(strExpiredFile, 0) != -1)
                CFile::Remove(strExpiredFile);
        }
        CATCH(CFileException, e)
        {
        }
        END_CATCH

        nHour = theTime.GetHour();
    }

    CFile* pLogFile = new CFile();
    CFileException ex;
    if (!pLogFile->Open(strFile, CFile::modeCreate | CFile::modeNoTruncate | CFile::modeWrite, &ex))
    {
        pLogFile->Close();
        delete pLogFile;
        return;
    }

    pLogFile->SeekToEnd();

    CT2A szFuncA(szFunc, CP_UTF8);
    CT2A szBufferA(szBuffer, CP_UTF8);
    CTime tNow = CTime::GetCurrentTime();
    size_t nLen = strlen(szFuncA) + strlen(szBufferA) + 32;
    char* szText = new char[nLen];
    int nLogLen = sprintf_s(szText, nLen, "%.2d:%.2d:%.2d - %s : %s\r\n",
        tNow.GetHour(), tNow.GetMinute(), tNow.GetSecond(),
        (LPCSTR)szFuncA, (LPCSTR)szBufferA);
    if (nLogLen > 0)
        pLogFile->Write(szText, (UINT)nLogLen);

    pLogFile->Close();
    delete pLogFile;
    delete[] szText;
}

CString CAppLog::GetLogDir()
{
    TCHAR szPath[MAX_PATH] = {0};
    GetModuleFileName(NULL, szPath, MAX_PATH);
    TCHAR* pSlash = _tcsrchr(szPath, _T('\\'));
    if (pSlash) *pSlash = _T('\0');

    CString strLogDir;
    strLogDir.Format(_T("%s\\Log"), szPath);

    if (_taccess(strLogDir, 0) == -1)
        ::CreateDirectory(strLogDir, NULL);

    return strLogDir;
}

CString CAppLog::GetLogFileName(int nDay)
{
    CString strFile;
    CString strLogDir = GetLogDir();
    strFile.Format(_T("%s\\LogEx%.2d.txt"), (LPCTSTR)strLogDir, nDay);
    return strFile;
}
