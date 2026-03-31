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

type ItemDetail struct {
	Name      string  `json:"name"`
	Category  *string `json:"category"`
	Effect    *string `json:"effect"`
	SpriteURL *string `json:"sprite_url"`
}

type MoveDetail struct {
	Name         string  `json:"name"`
	Type         *string `json:"type"`
	Category     *string `json:"category"`
	Power        *int    `json:"power"`
	Accuracy     *int    `json:"accuracy"`
	PP           *int    `json:"pp"`
	Effect       *string `json:"effect"`
	EffectChance *int    `json:"effect_chance"`
}

type AbilityDetail struct {
	Name        string  `json:"name"`
	Description *string `json:"description"`
	Generation  *int    `json:"generation"`
}

type AbilityPokemon struct {
	PokemonName string `json:"pokemon_name"`
	IsHidden    bool   `json:"is_hidden"`
}

type PokedexEntry struct {
	GameVersion string `json:"game_version"`
	FlavorText  string `json:"flavor_text"`
}

type Nature struct {
	Name          string  `json:"name"`
	IncreasedStat *string `json:"increased_stat"`
	DecreasedStat *string `json:"decreased_stat"`
}

type LocationEncounter struct {
	Region          string   `json:"region"`
	RouteName       string   `json:"route_name"`
	PokemonName     string   `json:"pokemon_name"`
	Games           []string `json:"games"`
	EncounterMethod *string  `json:"encounter_method"`
	Rarity          *string  `json:"rarity"`
	LevelRange      *string  `json:"level_range"`
	TimeOfDay       *string  `json:"time_of_day"`
}

type Berry struct {
	Name             string  `json:"name"`
	NaturalGiftType  *string `json:"natural_gift_type"`
	NaturalGiftPower *int    `json:"natural_gift_power"`
	SizeMM           *int    `json:"size_mm"`
	Firmness         *string `json:"firmness"`
	Effect           *string `json:"effect"`
	GrowthTime       *int    `json:"growth_time"`
}

type BerryFlavor struct {
	Flavor  string `json:"flavor"`
	Potency int    `json:"potency"`
}

type ItemLocation struct {
	ItemName string  `json:"item_name"`
	Game     string  `json:"game"`
	Location string  `json:"location"`
	Method   *string `json:"method"`
}

type TmLocation struct {
	TmNumber string `json:"tm_number"`
	MoveName string `json:"move_name"`
	Game     string `json:"game"`
	Location string `json:"location"`
}

type WildHeldItem struct {
	PokemonName string `json:"pokemon_name"`
	Game        string `json:"game"`
	ItemName    string `json:"item_name"`
	Rarity      string `json:"rarity"`
}

type PokemonBiology struct {
	PokemonName string `json:"pokemon_name"`
	Biology     string `json:"biology"`
}

type PokemonName struct {
	Language      string `json:"language"`
	LocalizedName string `json:"localized_name"`
}

type PokemonSprite struct {
	SpriteType string `json:"sprite_type"`
	Generation string `json:"generation"`
	URL        string `json:"url"`
}

type PokemonGameLocation struct {
	PokemonName string  `json:"pokemon_name"`
	Game        string  `json:"game"`
	Location    string  `json:"location"`
	Method      *string `json:"method"`
}
