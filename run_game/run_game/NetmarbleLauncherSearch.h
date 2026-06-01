#pragma once

#include "GameInstallSearchCommon.h"

class CNetmarbleLauncherSearch
{
public:
    explicit CNetmarbleLauncherSearch(const CGameInfo& gameInfo);

    BOOL Search(CGameInstallInfo& info);

private:
    const CGameInfo& m_GameInfo;
};
