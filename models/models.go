package models

type Pokemon struct {
	Name           string   `json:"name"`
	URL            *string  `json:"url"`
	NationalNo     *string  `json:"national_no"`
	Types          []string `json:"types"`
	Species        *string  `json:"species"`
	Height         *string  `json:"height"`
	Weight         *string  `json:"weight"`
	Abilities      []string `json:"abilities"`
	EVYield        *string  `json:"ev_yield"`
	CatchRate      *string  `json:"catch_rate"`
	BaseFriendship *string  `json:"base_friendship"`
	BaseExp        *string  `json:"base_exp"`
	GrowthRate     *string  `json:"growth_rate"`
	EggGroups      []string `json:"egg_groups"`
	GenderRatio    *string  `json:"gender_ratio"`
	EggCycles      *string  `json:"egg_cycles"`
	HP             *int     `json:"hp"`
	Attack         *int     `json:"attack"`
	Defense        *int     `json:"defense"`
	SpAtk          *int     `json:"sp_atk"`
	SpDef          *int     `json:"sp_def"`
	Speed          *int     `json:"speed"`
	Total          *int     `json:"total"`
}

type TypeDefense struct {
	TypeName   string  `json:"type_name"`
	Multiplier float32 `json:"multiplier"`
}

type Evolution struct {
	Number      *string  `json:"number"`
	Name        string   `json:"name"`
	URL         *string  `json:"url"`
	Types       []string `json:"types"`
	EvolvesVia  *string  `json:"evolves_via"`
	EvolvesFrom *string  `json:"evolves_from"`
	ChainOrder  int      `json:"chain_order"`
}

type Move struct {
	LearnMethod string `json:"learn_method"`
	LevelOrTM   string `json:"level_or_tm"`
	Name        string `json:"name"`
	Type        string `json:"type"`
	Category    string `json:"category"`
	Power       *int   `json:"power"`
	Accuracy    *int   `json:"accuracy"`
}

type Location struct {
	Games     []string `json:"games"`
	Locations []string `json:"locations"`
}

type RegionalDexEntry struct {
	DexNumber   int      `json:"dex_number"`
	PokemonName string   `json:"pokemon_name"`
	Types       []string `json:"types"`
}

type NationalDexEntry struct {
	NationalNo  int    `json:"national_no"`
	PokemonName string `json:"pokemon_name"`
}

type PokemonListEntry struct {
	Name       string   `json:"name"`
	NationalNo *string  `json:"national_no"`
	Types      []string `json:"types"`
}
